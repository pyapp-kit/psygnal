from contextlib import contextmanager
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Iterator,
    Set,
    Type,
    Union,
    cast,
)

from ._evented_model_shared import NULL, EventedMetaclass, dataclass_transform
from ._group import SignalGroup
from ._group_descriptor import _check_field_equality

if TYPE_CHECKING:
    import pydantic.v1.main as pydantic_main
    from pydantic.v1 import BaseModel, PrivateAttr
    from pydantic.v1.fields import Field, FieldInfo

    from ._evented_model_shared import EqOperator
    from ._signal import SignalInstance


else:
    import pydantic.main as pydantic_main
    from pydantic import BaseModel, PrivateAttr
    from pydantic.fields import Field, FieldInfo


@dataclass_transform(kw_only_default=True, field_specifiers=(Field, FieldInfo))
class EventedModel(BaseModel, metaclass=EventedMetaclass):
    """A pydantic BaseModel that emits a signal whenever a field value is changed.

    !!! important

        This class requires `pydantic` to be installed.
        You can install directly (`pip install pydantic`) or by using the psygnal
        extra: `pip install psygnal[pydantic]`

    In addition to standard pydantic `BaseModel` properties
    (see [pydantic docs](https://pydantic-docs.helpmanual.io/usage/models/)),
    this class adds the following:

    1. gains an `events` attribute that is an instance of [`psygnal.SignalGroup`][].
       This group will have a signal for each field in the model (excluding private
       attributes and non-mutable fields).  Whenever a field in the model is mutated,
       the corresponding signal will emit with the new value (see example below).

    2. Gains support for properties and property.setters (not supported in pydantic's
       BaseModel).  Enable by adding `allow_property_setters = True` to your model
       `Config`.

    3. If you would like properties (i.e. "computed fields") to emit an event when
       one of the model fields it depends on is mutated you must set one of the
       following options in the `Config`:

        - `property_dependencies` may be a `Dict[str, List[str]]`, where the
          keys are the names of properties, and the values are a list of field names
          (strings) that the property depends on for its value
        - `guess_property_dependencies` may be set to `True` to "guess" property
          dependencies by inspecting the source code of the property getter for.

    4. If you would like to allow custom fields to provide their own json_encoders, you
       can either use the standard pydantic method of adding json_encoders to your
       model, for each field type you'd like to support:
       https://pydantic-docs.helpmanual.io/usage/exporting_models/#json_encoders
       This `EventedModel` class will additionally look for a `_json_encode` method
       on any field types in the model.  If a field type declares a `_json_encode`
       method, it will be added to the
       [`json_encoders`](https://pydantic-docs.helpmanual.io/usage/exporting_models/#json_encoders)
       dict in the model `Config`.

    Examples
    --------
    Standard EventedModel example:

    ```python
    class MyModel(EventedModel):
        x: int = 1

    m = MyModel()
    m.events.x.connect(lambda v: print(f'new value is {v}'))
    m.x = 3  # prints 'new value is 3'
    ```

    An example of using property_setters and emitting signals when a field dependency
    is mutated.

    ```python
    class MyModel(EventedModel):
        a: int = 1
        b: int = 1

        @property
        def c(self) -> List[int]:
            return [self.a, self.b]

        @c.setter
        def c(self, val: Sequence[int]) -> None:
            self.a, self.b = val

        class Config:
            allow_property_setters = True
            property_dependencies = {"c": ["a", "b"]}

    m = MyModel()
    assert m.c == [1, 1]
    m.events.c.connect(lambda v: print(f"c updated to {v}"))
    m.a = 2  # prints 'c updated to [2, 1]'
    ```

    """

    # add private attributes for event emission
    _events: ClassVar[SignalGroup] = PrivateAttr()

    # mapping of name -> property obj for methods that are property setters
    __property_setters__: ClassVar[Dict[str, property]]
    # mapping of field name -> dependent set of property names
    # when field is changed, an event for dependent properties will be emitted.
    __field_dependents__: ClassVar[Dict[str, Set[str]]]
    __eq_operators__: ClassVar[Dict[str, "EqOperator"]]
    __slots__ = {"__weakref__"}
    __signal_group__: ClassVar[Type[SignalGroup]]
    # pydantic BaseModel configuration.  see:
    # https://pydantic-docs.helpmanual.io/usage/model_config/

    class Config:
        # this seems to be necessary for the _json_encoders trick to work
        json_encoders: ClassVar[dict] = {"____": None}

    def __init__(_model_self_, **data: Any) -> None:
        super().__init__(**data)
        Group = _model_self_.__signal_group__
        # the type error is "cannot assign to a class variable" ...
        # but if we don't use `ClassVar`, then the `dataclass_transform` decorator
        # will add _events: SignalGroup to the __init__ signature, for *all* user models
        _model_self_._events = Group(_model_self_)  # type: ignore [misc]

    def _super_setattr_(self, name: str, value: Any) -> None:
        # pydantic will raise a ValueError if extra fields are not allowed
        # so we first check to see if this field has a property.setter.
        # if so, we use it instead.
        if name in self.__property_setters__:
            self.__property_setters__[name].fset(self, value)  # type: ignore
        else:
            super().__setattr__(name, value)

    def __setattr__(self, name: str, value: Any) -> None:
        if (
            name == "_events"
            or not hasattr(self, "_events")  # can happen on init
            or name not in self._events
        ):
            # fallback to default behavior
            return self._super_setattr_(name, value)

        # if there are no listeners, we can just set the value without emitting
        # so first check if there are any listeners for this field or any of its
        # dependent properties.
        # note that ALL signals will have at least one listener simply by nature of
        # being in the `self._events` SignalGroup.
        group = self._events
        signal_instance: SignalInstance = group[name]
        deps_with_callbacks = {
            dep_name
            for dep_name in self.__field_dependents__.get(name, ())
            if len(group[dep_name])
        }
        if (
            len(signal_instance) < 1  # the signal itself has no listeners
            and not deps_with_callbacks  # no dependent properties with listeners
            and not len(group._psygnal_relay)  # no listeners on the SignalGroup
        ):
            return self._super_setattr_(name, value)

        # grab the current value and those of any dependent properties
        # so that we can check if they have changed after setting the value
        before = getattr(self, name, object())
        deps_before: Dict[str, Any] = {
            dep: getattr(self, dep) for dep in deps_with_callbacks
        }

        # set value using original setter
        with signal_instance.blocked():
            self._super_setattr_(name, value)

        # if the value has changed we emit the event with new value
        after = getattr(self, name)
        if not _check_field_equality(type(self), name, after, before):
            signal_instance.emit(after)  # emit event

            # also emit events for any dependent attributes that have changed as well
            for dep, before_val in deps_before.items():
                after_val = getattr(self, dep)
                if not _check_field_equality(type(self), dep, after_val, before_val):
                    getattr(self._events, dep).emit(after_val)

    # expose the private SignalGroup publically
    @property
    def events(self) -> SignalGroup:
        """Return the `SignalGroup` containing all events for this model."""
        return self._events

    @property
    def _defaults(self) -> dict:
        return _get_defaults(self)

    def reset(self) -> None:
        """Reset the state of the model to default values."""
        for name, value in self._defaults.items():
            if isinstance(value, EventedModel):
                cast("EventedModel", getattr(self, name)).reset()
            elif (
                self.__config__.allow_mutation
                and self.__fields__[name].field_info.allow_mutation
            ):
                setattr(self, name, value)

    def update(self, values: Union["EventedModel", dict], recurse: bool = True) -> None:
        """Update a model in place.

        Parameters
        ----------
        values : Union[dict, EventedModel]
            Values to update the model with. If an EventedModel is passed it is
            first converted to a dictionary. The keys of this dictionary must
            be found as attributes on the current model.
        recurse : bool
            If True, recursively update fields that are EventedModels.
            Otherwise, just update the immediate fields of this EventedModel,
            which is useful when the declared field type (e.g. ``Union``) can have
            different realized types with different fields.
        """
        if isinstance(values, BaseModel):
            values = values.dict()
        if not isinstance(values, dict):  # pragma: no cover
            raise TypeError(f"values must be a dict or BaseModel. got {type(values)}")

        with self.events._psygnal_relay.paused():  # TODO: reduce?
            for key, value in values.items():
                field = getattr(self, key)
                if isinstance(field, EventedModel) and recurse:
                    field.update(value, recurse=recurse)
                else:
                    setattr(self, key, value)

    def __eq__(self, other: Any) -> bool:
        """Check equality with another object.

        We override the pydantic approach (which just checks
        ``self.dict() == other.dict()``) to accommodate more complicated types
        like arrays, whose truth value is often ambiguous. ``__eq_operators__``
        is constructed in ``EqualityMetaclass.__new__``
        """
        if not isinstance(other, EventedModel):
            return self.dict() == other  # type: ignore

        for f_name, _ in self.__eq_operators__.items():
            if not hasattr(self, f_name) or not hasattr(other, f_name):
                return False  # pragma: no cover
            a = getattr(self, f_name)
            b = getattr(other, f_name)
            if not _check_field_equality(type(self), f_name, a, b):
                return False
        return True

    @contextmanager
    def enums_as_values(self, as_values: bool = True) -> Iterator[None]:
        """Temporarily override how enums are retrieved.

        Parameters
        ----------
        as_values : bool
            Whether enums should be shown as values (or as enum objects),
            by default `True`
        """
        before = getattr(self.Config, "use_enum_values", NULL)
        self.Config.use_enum_values = as_values  # type: ignore
        try:
            yield
        finally:
            if before is not NULL:
                self.Config.use_enum_values = before  # type: ignore  # pragma: no cover
            else:
                delattr(self.Config, "use_enum_values")


def _get_defaults(obj: BaseModel) -> Dict[str, Any]:
    """Get possibly nested default values for a Model object."""
    dflt = {}
    for k, v in obj.__fields__.items():
        d = v.get_default()
        if d is None and isinstance(v.type_, pydantic_main.ModelMetaclass):
            d = _get_defaults(v.type_)  # pragma: no cover
        dflt[k] = d
    return dflt
