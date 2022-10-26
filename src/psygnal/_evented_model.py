from __future__ import annotations

import sys
import warnings
from contextlib import contextmanager
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterator,
    Set,
    Type,
    Union,
    cast,
    no_type_check,
)

import pydantic.main
from pydantic import BaseModel, PrivateAttr, utils

from ._evented_decorator import _check_field_equality, _pick_equality_operator
from ._group import SignalGroup
from ._signal import Signal, SignalInstance

if TYPE_CHECKING:
    import inspect

    from pydantic import BaseConfig
    from pydantic.fields import ModelField

    ConfigType = Type[BaseConfig]
    EqOperator = Callable[[Any, Any], bool]

_NULL = object()
ALLOW_PROPERTY_SETTERS = "allow_property_setters"
PROPERTY_DEPENDENCIES = "property_dependencies"
GUESS_PROPERTY_DEPENDENCIES = "guess_property_dependencies"


@contextmanager
def no_class_attributes() -> Iterator[None]:  # pragma: no cover
    """Context in which pydantic.main.ClassAttribute just passes value 2.

    Due to a very annoying decision by PySide2, all class ``__signature__``
    attributes may only be assigned **once**.  (This seems to be regardless of
    whether the class has anything to do with PySide2 or not).  Furthermore,
    the PySide2 ``__signature__`` attribute seems to break the python
    descriptor protocol, which means that class attributes that have a
    ``__get__`` method will not be able to successfully retrieve their value
    (instead, the descriptor object itself will be accessed).

    This plays terribly with Pydantic, which assigns a ``ClassAttribute``
    object to the value of ``cls.__signature__`` in ``ModelMetaclass.__new__``
    in order to avoid masking the call signature of object instances that have
    a ``__call__`` method (https://github.com/samuelcolvin/pydantic/pull/1466).

    So, because we only get to set the ``__signature__`` once, this context
    manager basically "opts-out" of pydantic's ``ClassAttribute`` strategy,
    thereby directly setting the ``cls.__signature__`` to an instance of
    ``inspect.Signature``.

    For additional context, see:
    - https://github.com/napari/napari/issues/2264
    - https://github.com/napari/napari/pull/2265
    - https://bugreports.qt.io/browse/PYSIDE-1004
    - https://codereview.qt-project.org/c/pyside/pyside-setup/+/261411
    """
    if "PySide2" not in sys.modules:
        yield
        return

    # monkey patch the pydantic ClassAttribute object
    # the second argument to ClassAttribute is the inspect.Signature object
    def _return2(x: str, y: inspect.Signature) -> inspect.Signature:
        return y

    setattr(pydantic.main, "ClassAttribute", _return2)
    try:
        yield
    finally:
        # undo our monkey patch
        setattr(pydantic.main, "ClassAttribute", utils.ClassAttribute)


class EventedMetaclass(pydantic.main.ModelMetaclass):
    """pydantic ModelMetaclass that preps "equality checking" operations.

    A metaclass is the thing that "constructs" a class, and ``ModelMetaclass``
    is where pydantic puts a lot of it's type introspection and ``ModelField``
    creation logic.  Here, we simply tack on one more function, that builds a
    ``cls.__eq_operators__`` dict which is mapping of field name to a function
    that can be called to check equality of the value of that field with some
    other object.  (used in ``EventedModel.__eq__``)

    This happens only once, when an ``EventedModel`` class is created (and not
    when each instance of an ``EventedModel`` is instantiated).
    """

    @no_type_check
    def __new__(
        mcs: type, name: str, bases: tuple, namespace: dict, **kwargs: Any
    ) -> EventedMetaclass:
        """Create new EventedModel class."""
        with no_class_attributes():
            cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        cls.__eq_operators__ = {}
        signals = {}
        fields: Dict[str, ModelField] = cls.__fields__
        for n, f in fields.items():
            cls.__eq_operators__[n] = _pick_equality_operator(f.type_)
            if f.field_info.allow_mutation:
                signals[n] = Signal(f.type_)

            # If a field type has a _json_encode method, add it to the json
            # encoders for this model.
            # NOTE: a _json_encode field must return an object that can be
            # passed to json.dumps ... but it needn't return a string.
            if hasattr(f.type_, "_json_encode"):
                encoder = f.type_._json_encode
                cls.__config__.json_encoders[f.type_] = encoder
                # also add it to the base config
                # required for pydantic>=1.8.0 due to:
                # https://github.com/samuelcolvin/pydantic/pull/2064
                EventedModel.__config__.json_encoders[f.type_] = encoder

        allow_props = getattr(cls.__config__, ALLOW_PROPERTY_SETTERS, False)

        # check for @_.setters defined on the class, so we can allow them
        # in EventedModel.__setattr__
        cls.__property_setters__ = {}
        if allow_props:
            for b in reversed(cls.__bases__):
                if hasattr(b, "__property_setters__"):
                    cls.__property_setters__.update(b.__property_setters__)
            for name, attr in namespace.items():
                if isinstance(attr, property) and attr.fset is not None:
                    cls.__property_setters__[name] = attr
                    signals[name] = Signal(object)
        else:
            for b in cls.__bases__:
                conf = getattr(b, "__config__", None)
                if conf and getattr(conf, ALLOW_PROPERTY_SETTERS, False):
                    raise ValueError(
                        "Cannot set 'allow_property_setters' to 'False' when base "
                        f"class {b} sets it to True"
                    )

        cls.__field_dependents__ = _get_field_dependents(cls)
        cls.__signal_group__ = type(f"{name}SignalGroup", (SignalGroup,), signals)
        return cls


def _get_field_dependents(cls: EventedModel) -> Dict[str, Set[str]]:
    """Return mapping of field name -> dependent set of property names.

    Dependencies may be declared in the Model Config to emit an event
    for a computed property when a model field that it depends on changes
    e.g.  (@property 'c' depends on model fields 'a' and 'b')

    Examples
    --------
        class MyModel(EventedModel):
            a: int = 1
            b: int = 1

            @property
            def c(self) -> List[int]:
                return [self.a, self.b]

            @c.setter
            def c(self, val: Sequence[int]):
                self.a, self.b = val

            class Config:
                property_dependencies={'c': ['a', 'b']}
    """
    deps: Dict[str, Set[str]] = {}

    cfg_deps = getattr(cls.__config__, PROPERTY_DEPENDENCIES, {})  # sourcery skip
    if cfg_deps:
        assert isinstance(cfg_deps, dict), "Config.property_dependencies must be a dict"
        for prop, fields in cfg_deps.items():
            if prop not in cls.__property_setters__:
                raise ValueError(
                    "Fields with dependencies must be property.setters."
                    f"{prop!r} is not."
                )
            for field in fields:
                if field not in cls.__fields__:
                    warnings.warn(f"Unrecognized field dependency: {field!r}")
                deps.setdefault(field, set()).add(prop)
    if getattr(cls.__config__, GUESS_PROPERTY_DEPENDENCIES, False):
        # if property_dependencies haven't been explicitly defined, we can glean
        # them from the property.fget code object:
        # SKIP THIS MAGIC FOR NOW?
        for prop, setter in cls.__property_setters__.items():
            if setter.fget is not None:
                for name in setter.fget.__code__.co_names:
                    if name in cls.__fields__:
                        deps.setdefault(name, set()).add(prop)
    return deps


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
    _events: SignalGroup = PrivateAttr()

    # mapping of name -> property obj for methods that are property setters
    __property_setters__: ClassVar[Dict[str, property]]
    # mapping of field name -> dependent set of property names
    # when field is changed, an event for dependent properties will be emitted.
    __field_dependents__: ClassVar[Dict[str, Set[str]]]
    __eq_operators__: ClassVar[Dict[str, EqOperator]]
    __slots__ = {"__weakref__"}
    __signal_group__: ClassVar[Type[SignalGroup]]
    # pydantic BaseModel configuration.  see:
    # https://pydantic-docs.helpmanual.io/usage/model_config/

    class Config:  # noqa
        # this seems to be necessary for the _json_encoders trick to work
        json_encoders = {"____": None}

    def __init__(_model_self_, **data: Any) -> None:
        super().__init__(**data)
        _model_self_._events = _model_self_.__signal_group__(_model_self_)

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
            or name not in self._events.signals
        ):
            # fallback to default behavior
            return self._super_setattr_(name, value)

        # grab current value
        before = getattr(self, name, object())

        # set value using original setter
        self._super_setattr_(name, value)

        # if different we emit the event with new value
        after = getattr(self, name)

        if not _check_field_equality(type(self), name, after, before):
            signal_instance: SignalInstance = getattr(self.events, name)
            signal_instance.emit(after)  # emit event

            # emit events for any dependent computed property setters as well
            for dep in self.__field_dependents__.get(name, ()):
                getattr(self.events, dep).emit(getattr(self, dep))

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

    def update(self, values: Union[EventedModel, dict], recurse: bool = True) -> None:
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

        with self.events.paused():  # TODO: reduce?
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
        before = getattr(self.Config, "use_enum_values", _NULL)
        self.Config.use_enum_values = as_values  # type: ignore
        try:
            yield
        finally:
            if before is not _NULL:
                self.Config.use_enum_values = before  # type: ignore  # pragma: no cover
            else:
                delattr(self.Config, "use_enum_values")


def _get_defaults(obj: BaseModel) -> Dict[str, Any]:
    """Get possibly nested default values for a Model object."""
    dflt = {}
    for k, v in obj.__fields__.items():
        d = v.get_default()
        if d is None and isinstance(v.type_, pydantic.main.ModelMetaclass):
            d = _get_defaults(v.type_)  # pragma: no cover
        dflt[k] = d
    return dflt
