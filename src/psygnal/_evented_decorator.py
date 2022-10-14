import contextlib
import inspect
import operator
import sys
from dataclasses import fields, is_dataclass
from functools import lru_cache
from typing import Any, Callable, Dict, Iterator, Tuple, Type, TypeGuard, TypeVar, cast

from pydantic import BaseModel

from ._group import SignalGroup
from ._signal import Signal, SignalInstance

_PARAMS = "__dataclass_params__"
with contextlib.suppress(ImportError):
    from dataclasses import _PARAMS  # type: ignore

T = TypeVar("T", bound=Type)
_PRIVATE_EVENTS_GROUP = "_psygnal_group"
_NULL = object()

EqOperator = Callable[[Any, Any], bool]
_EQ_OPERATORS: Dict[Type, Dict[str, EqOperator]] = {}

_EQ_OPERATOR_NAME = "__eq_operators__"


def _get_eq_operator_map(cls: Type) -> Dict[str, EqOperator]:
    # if the class has an __eq_operators__ attribute, we use it
    # otherwise use/create the entry for `cls` in the global _EQ_OPERATORS map
    if hasattr(cls, _EQ_OPERATOR_NAME):
        return getattr(cls, _EQ_OPERATOR_NAME)  # type: ignore
    else:
        return _EQ_OPERATORS.setdefault(cls, {})


def _check_field_equality(
    cls: Type, name: str, before: Any, after: Any, _fail: bool = False
) -> bool:
    """ "Test if two values are equal for a given field.

    This function will use the `__eq_operators__` attribute of the class if
    present, otherwise it will use the default equality operator for the type.

    Parameters
    ----------
    cls : type
        The class that contains the field.
    name : str
        The name of the field.
    before : Any
        The value of the field before the change.
    after : Any
        The value of the field after the change.
    _fail : bool, optional
        If True, raise a ValueError if the field is not found in the class.
        by default False

    Returns
    -------
    bool
        True if the values are equal, False otherwise.
    """

    if before is _NULL:
        return after is _NULL

    eq_map = _get_eq_operator_map(cls)

    # get and execute the equality operator for the field
    are_equal = eq_map.setdefault(name, operator.eq)
    try:
        # may fail depending on the __eq__ method for the type
        return bool(are_equal(after, before))
    except Exception:
        if _fail:
            raise  # pragma: no cover

        np = sys.modules.get("numpy", None)
        if (
            hasattr(after, "__array__")
            and np is not None
            and are_equal is not np.array_equal
        ):
            eq_map[name] = np.array_equal
            return _check_field_equality(cls, name, before, after, _fail=False)
        else:
            eq_map[name] = operator.is_
            return _check_field_equality(cls, name, before, after, _fail=True)


def __setattr_and_emit__(self: Any, name: str, value: Any) -> None:
    if name == _PRIVATE_EVENTS_GROUP:
        # fallback to default behavior
        # super(type(self), self).__setattr__(name, value)
        object.__setattr__(self, name, value)
        return

    try:
        group = getattr(self, _PRIVATE_EVENTS_GROUP)
        signal_instance: SignalInstance = getattr(group, name)
    except AttributeError:
        super(type(self), self).__setattr__(name, value)
        return

    # grab current value
    before = getattr(self, name, _NULL)

    # set value using original setter
    super(type(self), self).__setattr__(name, value)

    # if different we emit the event with new value
    after = getattr(self, name)

    if not _check_field_equality(type(self), name, before, after):
        signal_instance.emit(after)  # emit event


def is_attrs_class(cls: Type) -> bool:
    attr = sys.modules.get("attr", None)
    return attr.has(cls) if attr is not None else False  # type: ignore


def is_pydantic_model(cls: Type) -> TypeGuard[BaseModel]:
    pydantic = sys.modules.get("pydantic", None)
    return pydantic is not None and issubclass(cls, pydantic.BaseModel)


def iter_fields(cls: Type) -> Iterator[Tuple[str, Type]]:
    """Iterate over all mutable fields in the class, including inherited fields."""

    if is_dataclass(cls):
        if getattr(cls, _PARAMS).frozen:
            raise TypeError("Frozen dataclasses cannot be made evented.")

        for d_field in fields(cls):
            yield d_field.name, d_field.type

    if is_attrs_class(cls):
        import attr

        for a_field in attr.fields(cls):
            yield a_field.name, cast("type", a_field.type)

    if is_pydantic_model(cls):
        for p_field in cls.__fields__.values():
            if p_field.field_info.allow_mutation:
                yield p_field.name, p_field.outer_type_


def _pick_equality_operator(type_: Type) -> EqOperator:
    np = sys.modules.get("numpy", None)
    if np is not None and hasattr(type_, "__array__"):
        return np.array_equal  # type: ignore
    return operator.eq


@lru_cache(maxsize=None)
def _build_dataclass_signal_group(cls: type) -> Type[SignalGroup]:
    signals = {}
    eq_map = _get_eq_operator_map(cls)
    for name, type_ in iter_fields(cls):
        eq_map.setdefault(name, _pick_equality_operator(type_))
        signals[name] = Signal(type_)

    return type(f"{cls.__name__}SignalGroup", (SignalGroup,), signals)


def evented(cls: T | None = None, events_namespace: str = "events") -> T:
    """A decorator to add events to a dataclass.

    note that this decorator will modify `cls` in place, as well as return it.
    """

    def _decorate(cls: T) -> T:
        assert isinstance(cls, type), "evented can only be used on classes"
        original_init = cls.__init__

        def __evented_init__(self: Any, *args: Any, **kwargs: Any) -> None:
            GroupCls = _build_dataclass_signal_group(cls)  # type: ignore
            setattr(self, _PRIVATE_EVENTS_GROUP, GroupCls())
            original_init(self, *args, **kwargs)

        cls.__setattr__ = __setattr_and_emit__  # type: ignore
        cls.__init__ = __evented_init__
        cls.__init__.__doc__ == original_init.__doc__

        if not hasattr(cls, "__signature__"):
            cls.__signature__ = inspect.signature(original_init)

        # expose the events as a property `events` by default, or as specified
        events_prop = property(lambda s: getattr(s, _PRIVATE_EVENTS_GROUP))
        setattr(cls, events_namespace, events_prop)

        return _add_slots(cls) if _is_slot_cls(cls) else cls

    return _decorate(cls) if cls is not None else _decorate


def _is_slot_cls(cls: Type) -> bool:
    return "__slots__" in cls.__dict__


def _add_slots(cls: T) -> T:
    # Need to create a new class, since we can't set __slots__
    #  after a class has been created.

    # Make sure __slots__ isn't already set.
    cls_dict = dict(cls.__dict__)

    __slots__ = {_PRIVATE_EVENTS_GROUP}
    if "__slots__" in cls.__dict__:
        for s in cls.__dict__["__slots__"]:
            __slots__.add(s)
            cls_dict.pop(s, None)

    # Create a new dict for our new class.
    cls_dict["__slots__"] = tuple(__slots__)
    # Remove __dict__ itself.
    cls_dict.pop("__dict__", None)

    # And finally create the class.
    qualname = getattr(cls, "__qualname__", None)
    cls = type(cls)(cls.__name__, cls.__bases__, cls_dict)
    if qualname is not None:
        cls.__qualname__ = qualname

    return cls
