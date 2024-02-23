from contextlib import contextmanager
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Iterator,
    Set,
    cast,
)

from pydantic import PrivateAttr
from pydantic.fields import Field, FieldInfo

from ._evented_model_shared import (
    NULL,
    _EBase,
    dataclass_transform,
)
from ._group import SignalGroup
from ._group_descriptor import _check_field_equality

if TYPE_CHECKING:
    from ._evented_model_shared import EqOperator
    from ._signal import SignalInstance


@dataclass_transform(kw_only_default=True, field_specifiers=(Field, FieldInfo))
class EventedModel(_EBase):
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
    # pydantic BaseModel configuration.  see:
    # https://pydantic-docs.helpmanual.io/usage/model_config/

    def _super_setattr_(self, name: str, value: Any) -> None:
        # pydantic will raise a ValueError if extra fields are not allowed
        # so we first check to see if this field has a property.setter.
        # if so, we use it instead.
        if name in self.__property_setters__:
            self.__property_setters__[name].fset(self, value)  # type: ignore
        elif name == "_events":
            # pydantic v2 prohibits shadowing class vars, on instances
            object.__setattr__(self, name, value)
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
        # note that ALL signals will have sat least one listener simply by nature of
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

    def reset(self) -> None:
        """Reset the state of the model to default values."""
        for name, value in self._defaults.items():
            if isinstance(value, EventedModel):
                cast("EventedModel", getattr(self, name)).reset()
            elif (
                not self.model_config.get("frozen")
                and not self.model_fields[name].frozen
            ):
                setattr(self, name, value)

    @classmethod
    @contextmanager
    def enums_as_values(
        cls, as_values: bool = True
    ) -> Iterator[None]:  # pragma: no cover
        """Temporarily override how enums are retrieved.

        Parameters
        ----------
        as_values : bool
            Whether enums should be shown as values (or as enum objects),
            by default `True`
        """
        before = cls.model_config.get("use_enum_values", NULL)
        cls.model_config["use_enum_values"] = as_values
        try:
            yield
        finally:
            if before is not NULL:  # pragma: no cover
                cls.model_config["use_enum_values"] = cast(bool, before)
            else:
                cls.model_config.pop("use_enum_values")
