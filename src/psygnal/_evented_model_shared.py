import sys
import warnings
from contextlib import contextmanager
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterator,
    NamedTuple,
    Set,
    no_type_check,
)

import pydantic

from ._group import SignalGroup
from ._group_descriptor import _pick_equality_operator
from ._signal import Signal

NULL = object()
ALLOW_PROPERTY_SETTERS = "allow_property_setters"
FIELD_DEPENDENCIES = "field_dependencies"
GUESS_PROPERTY_DEPENDENCIES = "guess_property_dependencies"
PYDANTIC_V1 = pydantic.version.VERSION.startswith("1")

if PYDANTIC_V1:
    import pydantic.main as pydantic_main
    from pydantic import utils
else:
    from pydantic._internal import _model_construction as pydantic_main  # type: ignore
    from pydantic._internal import _utils as utils  # type: ignore

if TYPE_CHECKING:
    from inspect import Signature

    from pydantic import ConfigDict
    from typing_extensions import dataclass_transform  # py311

    EqOperator = Callable[[Any, Any], bool]
else:
    try:
        # py311
        from typing_extensions import dataclass_transform as dataclass_transform
    except ImportError:  # pragma: no cover

        def dataclass_transform(*args, **kwargs):
            return lambda a: a


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


class FieldInfo(NamedTuple):
    annotation: type[Any] | None
    frozen: bool | None


class GetAttrAsItem:
    def __init__(self, obj: Any) -> None:
        self._obj = obj

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self._obj, key, default)


def _get_fields(cls: type) -> dict[str, FieldInfo]:
    if PYDANTIC_V1:
        return {
            k: FieldInfo(annotation=f.type_, frozen=not f.field_info.allow_mutation)
            for k, f in cls.__fields__.items()
        }
    else:
        return cls.model_fields


@no_type_check
def _get_config(cls: type) -> "ConfigDict":
    if PYDANTIC_V1:
        return GetAttrAsItem(cls.__config__)
    else:
        return cls.model_config


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

    __property_setters__: dict[str, property]

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

        for n, f in model_fields.items():
            cls.__eq_operators__[n] = _pick_equality_operator(f.annotation)
            if not f.frozen:
                signals[n] = Signal(f.annotation)

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
                    signals[key] = Signal(object)
        else:
            for b in cls.__bases__:
                if not (hasattr(b, "model_config") or hasattr(b, "__config__")):
                    continue
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
