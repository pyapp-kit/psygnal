import sys
import warnings
from contextlib import contextmanager, suppress
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterator,
    Mapping,
    NamedTuple,
    Set,
    Type,
    Union,
    cast,
    no_type_check,
)

import pydantic
from pydantic import PrivateAttr

from ._group import SignalGroup
from ._group_descriptor import _check_field_equality, _pick_equality_operator
from ._signal import Signal

PYDANTIC_V1 = pydantic.version.VERSION.startswith("1")

if TYPE_CHECKING:
    from inspect import Signature

    from pydantic import ConfigDict
    from pydantic._internal import _model_construction as pydantic_main
    from pydantic._internal import _utils as utils
    from typing_extensions import dataclass_transform as dataclass_transform  # py311

    from ._signal import RecursionMode, SignalInstance

    EqOperator = Callable[[Any, Any], bool]
else:
    if PYDANTIC_V1:
        import pydantic.main as pydantic_main
        from pydantic import utils
    else:
        from pydantic._internal import _model_construction as pydantic_main
        from pydantic._internal import _utils as utils

    try:
        # py311
        from typing_extensions import dataclass_transform
    except ImportError:  # pragma: no cover

        def dataclass_transform(*args, **kwargs):
            return lambda a: a


NULL = object()
ALLOW_PROPERTY_SETTERS = "allow_property_setters"
FIELD_DEPENDENCIES = "field_dependencies"
GUESS_PROPERTY_DEPENDENCIES = "guess_property_dependencies"
RECURSION_MODE = "recursion_mode"
DEFAULT_RECURSION_MODE: "RecursionMode" = "deferred"


@contextmanager
def no_class_attributes() -> Iterator[None]:  # pragma: no cover
    """Context in which pydantic_main.ClassAttribute just passes value 2.

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
    def _return2(x: str, y: "Signature") -> "Signature":
        return y

    pydantic_main.ClassAttribute = _return2  # type: ignore
    try:
        yield
    finally:
        # undo our monkey patch
        pydantic_main.ClassAttribute = utils.ClassAttribute  # type: ignore


if not PYDANTIC_V1:

    def _get_defaults(
        obj: Union[pydantic.BaseModel, Type[pydantic.BaseModel]],
    ) -> Dict[str, Any]:
        """Get possibly nested default values for a Model object."""
        dflt = {}
        for k, v in obj.model_fields.items():
            d = v.get_default()
            if (
                d is None
                and isinstance(v.annotation, type)
                and issubclass(v.annotation, pydantic.BaseModel)
            ):
                d = _get_defaults(v.annotation)  # pragma: no cover
            dflt[k] = d
        return dflt

    def _get_config(cls: pydantic.BaseModel) -> "ConfigDict":
        return cls.model_config

    def _get_fields(cls: pydantic.BaseModel) -> Dict[str, pydantic.fields.FieldInfo]:
        return cls.model_fields

    def _model_dump(obj: pydantic.BaseModel) -> dict:
        return obj.model_dump()

else:

    @no_type_check
    def _get_defaults(obj: pydantic.BaseModel) -> Dict[str, Any]:
        """Get possibly nested default values for a Model object."""
        dflt = {}
        for k, v in obj.__fields__.items():
            d = v.get_default()
            if d is None and isinstance(v.type_, pydantic_main.ModelMetaclass):
                d = _get_defaults(v.type_)  # pragma: no cover
            dflt[k] = d
        return dflt

    class GetAttrAsItem:
        def __init__(self, obj: Any) -> None:
            self._obj = obj

        def get(self, key: str, default: Any = None) -> Any:
            return getattr(self._obj, key, default)

    @no_type_check
    def _get_config(cls: type) -> "ConfigDict":
        return GetAttrAsItem(cls.__config__)

    class FieldInfo(NamedTuple):
        annotation: Union[Type[Any], None]
        frozen: Union[bool, None]

    @no_type_check
    def _get_fields(cls: type) -> Dict[str, FieldInfo]:
        return {
            k: FieldInfo(annotation=f.type_, frozen=not f.field_info.allow_mutation)
            for k, f in cls.__fields__.items()
        }

    def _model_dump(obj: pydantic.BaseModel) -> dict:
        return obj.dict()


class ComparisonDelayer:
    """Context that delays before/after comparisons until exit."""

    def __init__(self, target: "EventedModel") -> None:
        self._target = target

    def __enter__(self) -> None:
        self._target._delay_check_semaphore += 1

    def __exit__(self, *_: Any, **__: Any) -> None:
        self._target._delay_check_semaphore -= 1
        self._target._check_if_values_changed_and_emit_if_needed()


class EventedMetaclass(pydantic_main.ModelMetaclass):
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

    __property_setters__: Dict[str, property]

    @no_type_check
    def __new__(
        mcs: type, name: str, bases: tuple, namespace: dict, **kwargs: Any
    ) -> "EventedMetaclass":
        """Create new EventedModel class."""
        with no_class_attributes():
            cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        cls.__eq_operators__ = {}
        signals = {}

        model_fields = _get_fields(cls)
        model_config = _get_config(cls)

        recursion_cfg = model_config.get(RECURSION_MODE, {})
        default_recursion: RecursionMode = DEFAULT_RECURSION_MODE
        recursion_map: Mapping[str, RecursionMode] = {}
        if isinstance(recursion_cfg, str):
            if recursion_cfg not in {"immediate", "deferred"}:
                raise ValueError(
                    f"Invalid recursion mode {default_recursion!r}. Must be "
                    "either 'immediate' or 'deferred'"
                )
            default_recursion = recursion_cfg
        else:
            if not isinstance(recursion_cfg, Mapping) or not all(
                x in {"immediate", "deferred"} for x in recursion_cfg.values()
            ):
                raise ValueError(
                    f"Invalid recursion mode {recursion_cfg!r}. Must be a mapping "
                    "of field names to 'immediate' or 'deferred'."
                )
            recursion_map = recursion_cfg

        for n, f in model_fields.items():
            cls.__eq_operators__[n] = _pick_equality_operator(f.annotation)
            if not f.frozen:
                recursion = recursion_map.get(n, default_recursion)
                signals[n] = Signal(f.annotation, recursion_mode=recursion)

            # If a field type has a _json_encode method, add it to the json
            # encoders for this model.
            # NOTE: a _json_encode field must return an object that can be
            # passed to json.dumps ... but it needn't return a string.
            if PYDANTIC_V1 and hasattr(f.annotation, "_json_encode"):
                encoder = f.annotation._json_encode
                cls.__config__.json_encoders[f.annotation] = encoder
                # also add it to the base config
                # required for pydantic>=1.8.0 due to:
                # https://github.com/samuelcolvin/pydantic/pull/2064
                for base in cls.__bases__:
                    if hasattr(base, "__config__"):
                        base.__config__.json_encoders[f.annotation] = encoder

        allow_props = model_config.get(ALLOW_PROPERTY_SETTERS, False)

        # check for @_.setters defined on the class, so we can allow them
        # in EventedModel.__setattr__
        cls.__property_setters__ = {}
        if allow_props:
            for b in reversed(cls.__bases__):
                if hasattr(b, "__property_setters__"):
                    cls.__property_setters__.update(b.__property_setters__)
            for key, attr in namespace.items():
                if isinstance(attr, property) and attr.fset is not None:
                    cls.__property_setters__[key] = attr
                    recursion = recursion_map.get(key, default_recursion)
                    signals[key] = Signal(object, recursion_mode=recursion)
        else:
            for b in cls.__bases__:
                with suppress(AttributeError):
                    conf = _get_config(b)
                    if conf and conf.get(ALLOW_PROPERTY_SETTERS, False):
                        raise ValueError(
                            "Cannot set 'allow_property_setters' to 'False' when base "
                            f"class {b} sets it to True"
                        )

        cls.__field_dependents__ = _get_field_dependents(
            cls, model_config, model_fields
        )
        cls.__signal_group__ = type(f"{name}SignalGroup", (SignalGroup,), signals)
        if not cls.__field_dependents__ and hasattr(cls, "_setattr_no_dependants"):
            cls._setattr_default = cls._setattr_no_dependants
        elif hasattr(cls, "_setattr_with_dependents"):
            cls._setattr_default = cls._setattr_with_dependents
        return cls


def _get_field_dependents(
    cls: "EventedMetaclass", model_config: dict, model_fields: dict
) -> Dict[str, Set[str]]:
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

    cfg_deps = model_config.get(FIELD_DEPENDENCIES, {})  # sourcery skip
    if not cfg_deps:
        cfg_deps = model_config.get("property_dependencies", {})
        if cfg_deps:
            warnings.warn(
                "The 'property_dependencies' configuration key is deprecated. "
                "Use 'field_dependencies' instead",
                DeprecationWarning,
                stacklevel=2,
            )

    if cfg_deps:
        if not isinstance(cfg_deps, dict):  # pragma: no cover
            raise TypeError(
                f"Config property_dependencies must be a dict, not {cfg_deps!r}"
            )
        for prop, fields in cfg_deps.items():
            if prop not in {*model_fields, *cls.__property_setters__}:
                raise ValueError(
                    "Fields with dependencies must be fields or property.setters."
                    f"{prop!r} is not."
                )
            for field in fields:
                if field not in model_fields:
                    warnings.warn(
                        f"Unrecognized field dependency: {field!r}", stacklevel=2
                    )
                deps.setdefault(field, set()).add(prop)
    if model_config.get(GUESS_PROPERTY_DEPENDENCIES, False):
        # if property_dependencies haven't been explicitly defined, we can glean
        # them from the property.fget code object:
        # SKIP THIS MAGIC FOR NOW?
        for prop, setter in cls.__property_setters__.items():
            if setter.fget is not None:
                for name in setter.fget.__code__.co_names:
                    if name in model_fields:
                        deps.setdefault(name, set()).add(prop)
    return deps


@dataclass_transform(kw_only_default=True, field_specifiers=(pydantic.Field,))
class EventedModel(pydantic.BaseModel, metaclass=EventedMetaclass):
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
    m.events.x.connect(lambda v: print(f"new value is {v}"))
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
            field_dependencies = {"c": ["a", "b"]}


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
    _changes_queue: Dict[str, Any] = PrivateAttr(default_factory=dict)
    _primary_changes: Set[str] = PrivateAttr(default_factory=set)
    _delay_check_semaphore: int = PrivateAttr(0)

    if PYDANTIC_V1:

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

    # expose the private SignalGroup publicly
    @property
    def events(self) -> SignalGroup:
        """Return the `SignalGroup` containing all events for this model."""
        return self._events

    @property
    def _defaults(self) -> Dict[str, Any]:
        return _get_defaults(self)

    def __eq__(self, other: Any) -> bool:
        """Check equality with another object.

        We override the pydantic approach (which just checks
        ``self.model_dump() == other.model_dump()``) to accommodate more complicated
        types like arrays, whose truth value is often ambiguous. ``__eq_operators__``
        is constructed in ``EqualityMetaclass.__new__``
        """
        if not isinstance(other, EventedModel):
            return bool(_model_dump(self) == other)

        for f_name, _ in self.__eq_operators__.items():
            if not hasattr(self, f_name) or not hasattr(other, f_name):
                return False  # pragma: no cover
            a = getattr(self, f_name)
            b = getattr(other, f_name)
            if not _check_field_equality(type(self), f_name, a, b):
                return False
        return True

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
        if isinstance(values, pydantic.BaseModel):
            values = _model_dump(values)

        if not isinstance(values, dict):  # pragma: no cover
            raise TypeError(f"values must be a dict or BaseModel. got {type(values)}")

        with self.events._psygnal_relay.paused():  # TODO: reduce?
            for key, value in values.items():
                field = getattr(self, key)
                if isinstance(field, EventedModel) and recurse:
                    field.update(value, recurse=recurse)
                else:
                    setattr(self, key, value)

    def reset(self) -> None:
        """Reset the state of the model to default values."""
        model_config = _get_config(self)
        model_fields = _get_fields(self)
        for name, value in self._defaults.items():
            if isinstance(value, EventedModel):
                cast("EventedModel", getattr(self, name)).reset()
            elif not model_config.get("frozen") and not model_fields[name].frozen:
                setattr(self, name, value)

    def _check_if_values_changed_and_emit_if_needed(self) -> None:
        """
        Check if field values changed and emit events if needed.

        The advantage of moving this to the end of all the modifications is
        that comparisons will be performed only once for every potential change.
        """
        if self._delay_check_semaphore > 0 or len(self._changes_queue) == 0:
            # do not run whole machinery if there is no need
            return
        to_emit = []
        for name in self._primary_changes:
            # primary changes should contains only fields
            # that are changed directly by assignment
            old_value = self._changes_queue[name]
            new_value = getattr(self, name)
            if not _check_field_equality(type(self), name, new_value, old_value):
                to_emit.append((name, new_value))
            self._changes_queue.pop(name)
        if not to_emit:
            # If no direct changes was made then we can skip whole machinery
            self._changes_queue.clear()
            self._primary_changes.clear()
            return
        for name, old_value in self._changes_queue.items():
            # check if any of dependent properties changed
            new_value = getattr(self, name)
            if not _check_field_equality(type(self), name, new_value, old_value):
                to_emit.append((name, new_value))
        self._changes_queue.clear()
        self._primary_changes.clear()

        with ComparisonDelayer(self):
            # Again delay comparison to avoid having events caused by callback functions
            for name, new_value in to_emit:
                getattr(self._events, name)(new_value)

    def __setattr__(self, name: str, value: Any) -> None:
        if (
            name == "_events"
            or not hasattr(self, "_events")  # can happen on init
            or name not in self._events
        ):
            # fallback to default behavior
            return self._super_setattr_(name, value)
        # the _setattr_default method is overridden in __new__ to be one of
        # `_setattr_no_dependants` or `_setattr_with_dependents`.
        self._setattr_default(name, value)

    def _super_setattr_(self, name: str, value: Any) -> None:
        # pydantic will raise a ValueError if extra fields are not allowed
        # so we first check to see if this field has a property.setter.
        # if so, we use it instead.
        if name in self.__property_setters__:
            self.__property_setters__[name].fset(self, value)  # type: ignore[misc]
        elif name == "_events":
            # pydantic v2 prohibits shadowing class vars, on instances
            object.__setattr__(self, name, value)
        else:
            super().__setattr__(name, value)

    def _setattr_default(self, name: str, value: Any) -> None:
        """Will be overwritten by metaclass __new__.

        It will become either `_setattr_no_dependants` (if the class has no
        properties and `__field_dependents__`), or `_setattr_with_dependents` if it
        does.
        """

    def _setattr_no_dependants(self, name: str, value: Any) -> None:
        """__setattr__ behavior when the class has no properties."""
        group = self._events
        signal_instance: SignalInstance = group[name]
        if len(signal_instance) < 1:
            return self._super_setattr_(name, value)
        old_value = getattr(self, name, object())
        self._super_setattr_(name, value)
        if not _check_field_equality(type(self), name, value, old_value):
            getattr(self._events, name)(value)

    def _setattr_with_dependents(self, name: str, value: Any) -> None:
        """__setattr__ behavior when the class does properties."""
        with ComparisonDelayer(self):
            self._setattr_impl(name, value)

    def _setattr_impl(self, name: str, value: Any) -> None:
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
        self._primary_changes.add(name)
        if name not in self._changes_queue:
            self._changes_queue[name] = getattr(self, name, object())

        for dep in deps_with_callbacks:
            if dep not in self._changes_queue:
                self._changes_queue[dep] = getattr(self, dep, object())
        self._super_setattr_(name, value)

    if PYDANTIC_V1:

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

    else:

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
