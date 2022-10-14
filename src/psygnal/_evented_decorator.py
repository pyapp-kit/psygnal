import contextlib
import inspect
import operator
import sys
import warnings
from dataclasses import fields, is_dataclass
from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from ._group import SignalGroup
from ._signal import Signal, SignalInstance

if TYPE_CHECKING:
    from typing import Literal, TypeGuard

    from pydantic import BaseModel


_DATACLASS_PARAMS = "__dataclass_params__"
with contextlib.suppress(ImportError):
    from dataclasses import _DATACLASS_PARAMS  # type: ignore

T = TypeVar("T", bound=Type)

EqOperator = Callable[[Any, Any], bool]
_EQ_OPERATORS: Dict[Type, Dict[str, EqOperator]] = {}
_EQ_OPERATOR_NAME = "__eq_operators__"
_PRIVATE_EVENTS_GROUP = "_psygnal_group"
_NULL = object()


def _get_eq_operator_map(cls: Type) -> Dict[str, EqOperator]:
    """Return the map of field_name -> equality operator for the class."""
    # if the class has an __eq_operators__ attribute, we use it
    # otherwise use/create the entry for `cls` in the global _EQ_OPERATORS map
    if hasattr(cls, _EQ_OPERATOR_NAME):
        return getattr(cls, _EQ_OPERATOR_NAME)  # type: ignore
    else:
        return _EQ_OPERATORS.setdefault(cls, {})


def _check_field_equality(
    cls: Type, name: str, before: Any, after: Any, _fail: bool = False
) -> bool:
    """Test if two values are equal for a given field.

    This function will look for a field-specific operator in the the `__eq_operators__`
    attribute of the class if present, otherwise it will use the default equality
    operator for the type.

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

        # if we fail, we try to pick a new equality operator
        # if it's a numpy array, we use np.array_equal
        # finally, fallback to operator.is_
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
    """New __setattr__ method that emits events when fields change."""
    if name == _PRIVATE_EVENTS_GROUP:
        # we're in our custom init.  just add the events group
        object.__setattr__(self, name, value)
        return

    # ensure we have a signal instance, before worrying about events at all.
    try:
        group = getattr(self, _PRIVATE_EVENTS_GROUP)
        signal_instance: SignalInstance = getattr(group, name)
    except AttributeError:  # pragma: no cover
        super(type(self), self).__setattr__(name, value)
        return

    # grab current value
    before = getattr(self, name, _NULL)

    # set value using original setter
    super(type(self), self).__setattr__(name, value)

    # if different we emit the event with new value
    after = getattr(self, name)

    # finally, emit the event if the value changed
    if not _check_field_equality(type(self), name, before, after):
        signal_instance.emit(after)


def is_attrs_class(cls: Type) -> bool:
    """Return True if the class is an attrs class."""
    attr = sys.modules.get("attr", None)
    return attr.has(cls) if attr is not None else False  # type: ignore


def is_pydantic_model(cls: Type) -> "TypeGuard[BaseModel]":
    """Return True if the class is a pydantic BaseModel."""
    pydantic = sys.modules.get("pydantic", None)
    return pydantic is not None and issubclass(cls, pydantic.BaseModel)


def iter_fields(cls: Type) -> Iterator[Tuple[str, Type]]:
    """Iterate over all mutable fields in the class, including inherited fields.

    This function recognizes dataclasses, attrs classes, and pydantic models.
    """
    if is_dataclass(cls):
        if getattr(cls, _DATACLASS_PARAMS).frozen:  # pragma: no cover
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
    """Get the default equality operator for a given type."""
    np = sys.modules.get("numpy", None)
    if np is not None and hasattr(type_, "__array__"):
        return np.array_equal  # type: ignore
    return operator.eq


@lru_cache(maxsize=None)
def _build_dataclass_signal_group(
    cls: Type, equality_operators: Optional[Iterable[Tuple[str, EqOperator]]] = None
) -> Type[SignalGroup]:
    """Build a SignalGroup with events for each field in a dataclass."""
    _equality_operators = dict(equality_operators) if equality_operators else {}
    signals = {}
    eq_map = _get_eq_operator_map(cls)
    for name, type_ in iter_fields(cls):
        if name in _equality_operators:
            assert callable(_equality_operators[name]), "EqOperator must be callable"
            eq_map[name] = _equality_operators[name]
        else:
            eq_map[name] = _pick_equality_operator(type_)
        signals[name] = Signal(type_)

    return type(f"{cls.__name__}SignalGroup", (SignalGroup,), signals)


@overload
def evented(
    cls: T,
    *,
    events_namespace: str = "events",
    equality_operators: Optional[Dict[str, EqOperator]] = None,
) -> T:
    ...


@overload
def evented(
    cls: "Literal[None]" = None,
    *,
    events_namespace: str = "events",
    equality_operators: Optional[Dict[str, EqOperator]] = None,
) -> Callable[[T], T]:
    ...


def evented(
    cls: Optional[T] = None,
    *,
    events_namespace: str = "events",
    equality_operators: Optional[Dict[str, EqOperator]] = None,
) -> Union[Callable[[T], T], T]:
    """A decorator to add events to a [dataclass][dataclasses.dataclass],
    [attrs](https://www.attrs.org), or [pydantic](https://pydantic-docs.helpmanual.io)
    model.

    Note that this decorator will modify `cls` *in place*, as well as return it.

    Parameters
    ----------
    cls : type
        The class to decorate.
    events_namespace : str
        The name of the namespace to add the events to, by default `"events"`
    equality_operators : Optional[Dict[str, Callable]]
        A dictionary mapping field names to equality operators (a function that takes
        two values and returns `True` if they are equal). These will be used to
        determine if a field has changed when setting a new value.  By default, this
        will use the `__eq__` method of the field type, or np.array_equal, for numpy
        arrays.  But you can provide your own if you want to customize how equality is
        checked. Alternatively, if the class has an `__eq_operators__` class attribute,
        it will be used.

    Returns
    -------
    type
        The decorated class, which gains a new SignalGroup instance at the
        `events_namespace` attribute (by default, `events`).

    Raises
    ------
    TypeError
        If the class is frozen or is not a class.

    Examples
    --------
    ```python
    from psygnal import evented
    from dataclasses import dataclass

    @evented
    @dataclass
    class Person:
        name: str
        age: int = 0
    ```
    """  # noqa: D
    _eqop = tuple(equality_operators.items()) if equality_operators else None

    def _decorate(cls: T) -> T:
        assert isinstance(cls, type), "evented can only be used on classes"
        Grp = _build_dataclass_signal_group(cls, _eqop)  # type: ignore
        if not Grp._signals_:
            warnings.warn(
                f"No mutable fields found in class {cls} no events will be emitted. "
                "(Is this a dataclass, attrs, or pydantic model?)"
            )
            return cls

        original_init = cls.__init__

        def __evented_init__(self: Any, *args: Any, **kwargs: Any) -> None:
            setattr(self, _PRIVATE_EVENTS_GROUP, Grp())
            original_init(self, *args, **kwargs)

        cls.__setattr__ = __setattr_and_emit__  # type: ignore
        cls.__init__ = __evented_init__
        cls.__init__.__doc__ = original_init.__doc__

        if not hasattr(cls, "__signature__"):
            cls.__signature__ = inspect.signature(original_init)

        # expose the events as a property `events` by default, or as specified
        events_prop = property(lambda s: getattr(s, _PRIVATE_EVENTS_GROUP))
        setattr(cls, events_namespace, events_prop)

        return _add_slots(cls) if "__slots__" in cls.__dict__ else cls

    return _decorate(cls) if cls is not None else _decorate


def _add_slots(cls: T) -> T:
    """Add __slots__ to support evented dataclasses with __slots__."""
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
    cls = type(cls)(cls.__name__, cls.__bases__, cls_dict)  # type: ignore
    if qualname is not None:
        cls.__qualname__ = qualname

    return cls
