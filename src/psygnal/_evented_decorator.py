import contextlib
import operator
import sys
from dataclasses import fields, is_dataclass
from functools import lru_cache
from typing import Any, Callable, Dict, Iterator, Tuple, Type

from ._group import SignalGroup
from ._signal import Signal, SignalInstance

_PARAMS = "__dataclass_params__"
with contextlib.suppress(ImportError):
    from dataclasses import _PARAMS  # type: ignore


_NULL = object()
EqOperator = Callable[[Any, Any], bool]

_EQ_OPERATORS: Dict[Type, EqOperator] = {}


def _check_field_equality(before: Any, after: Any, _fail: bool = False) -> bool:
    if before is _NULL:
        return after is _NULL

    after_type = type(after)
    are_equal = _EQ_OPERATORS.get(after_type, operator.eq)
    try:
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
            _EQ_OPERATORS[after_type] = np.array_equal
            return _check_field_equality(before, after, _fail=False)
        else:
            _EQ_OPERATORS[after_type] = operator.is_
            return _check_field_equality(before, after, _fail=True)


def setattr_and_emit(obj: Any, name: str, value: Any) -> None:
    if (
        name == "_events"
        or not hasattr(obj, "_events")  # can happen on init
        or name not in obj._events.signals
    ):
        # fallback to default behavior
        super(type(obj), obj).__setattr__(name, value)
        return

    # grab current value
    before = getattr(obj, name, _NULL)

    # set value using original setter
    super(type(obj), obj).__setattr__(name, value)

    # if different we emit the event with new value
    after = getattr(obj, name)

    if not _check_field_equality(before, after):
        signal_instance: SignalInstance = getattr(obj.events, name)
        signal_instance.emit(after)  # emit event


def _pick_equality_operator(type_: Type) -> EqOperator:
    import operator

    return operator.eq


def iter_fields(cls) -> Iterator[Tuple[str, Type]]:
    """Iterate over all mutable fields in the class, including inherited fields."""

    if is_dataclass(cls):
        if getattr(cls, _PARAMS).frozen:
            raise TypeError("Frozen dataclasses are not supported")

        for field in fields(cls):
            yield field.name, field.type


@lru_cache
def build_signal_group(cls):
    signals = {}
    for name, type_ in iter_fields(cls):
        if type_ not in _EQ_OPERATORS:
            _EQ_OPERATORS[type_] = _pick_equality_operator(type_)
        signals[name] = Signal(type_)

    return type(f"{cls.__name__}SignalGroup", (SignalGroup,), signals)


def evented(cls):
    original_init = cls.__init__

    def new_init(self, *args, **kwargs) -> None:
        print("new init")
        self._events = build_signal_group(cls)()
        original_init(self, *args)

    cls.__setattr__ = setattr_and_emit
    setattr(cls, "__init__", new_init)
    print("set")
    cls.events = property(lambda self: self._events)
    return cls
