# pyright: reportUnnecessaryTypeIgnoreComment=true
"""Static checks of typed signals, run with mypy and pyright.

Lines ending in `# type: ignore` must produce an error in both checkers;
mypy's `--warn-unused-ignores` and pyright's `reportUnnecessaryTypeIgnoreComment`
fail the run when one does not.
"""

from collections.abc import Callable
from functools import partial
from inspect import Signature
from typing import Any, assert_type

from psygnal import Signal, SignalInstance
from psygnal.containers import EventedObjectProxy, Selection


class Model:
    """Signals of every kind the checkers must infer."""

    zero = Signal()
    one = Signal(int)
    union = Signal(str | None)
    two = Signal(int, list[str])
    raw = Signal(Signature())


m = Model()
assert_type(Model.one, Signal[int])
assert_type(m.one, SignalInstance[int])
assert_type(m.zero, SignalInstance[()])
assert_type(m.union, SignalInstance[str | None])
assert_type(m.two, SignalInstance[int, list[str]])
assert_type(m.raw, SignalInstance[*tuple[Any, ...]])
assert_type(SignalInstance((int,)), SignalInstance[*tuple[Any, ...]])

m.one.emit(1)
m.one.emit(1, check_nargs=True, check_types=True)
m.one.emit_fast(1)
m.one(1)
m.union.emit(None)
m.raw.emit(1, "anything")
m.one.emit("x")  # type: ignore
m.one.emit(1, 2)  # type: ignore
m.zero.emit(1)  # type: ignore
m.one.emit_fast("x")  # type: ignore
Signal(1)  # type: ignore


class MyInstance(SignalInstance):
    """A custom signal instance class."""


MySignal = partial(Signal, signal_instance_class=MyInstance)


class PartialModel:
    """Signals declared through a partial of Signal."""

    one = MySignal(int)


PartialModel().one.emit(1)


def on_int(v: int) -> int:
    """Take an int."""
    return v


def on_str(v: str) -> None:
    """Take a str."""


def on_none() -> None:
    """Take nothing."""


def on_default(v: int, extra: int = 0) -> None:
    """Take an int and an optional int."""


def on_varargs(*args: Any) -> None:
    """Take anything."""


async def on_async(v: int) -> None:
    """Take an int in a coroutine."""


def on_three(a: int, b: list[str], c: int) -> None:
    """Take three arguments."""


class Handler:
    """Owner of a bound method slot."""

    def method(self, v: int) -> None:
        """Take an int."""


assert_type(m.one.connect(on_int), Callable[[int], int])
m.one.connect(on_none)
m.one.connect(on_default)
m.one.connect(on_varargs)
m.one.connect(on_async)
m.one.connect(Handler().method)
m.one.connect(partial(on_default, extra=1))
m.two.connect(on_int)
m.one.connect(on_str)  # type: ignore
m.two.connect(on_three)  # type: ignore
m.zero.connect(on_int)  # type: ignore


@m.one.connect(thread="main")
def decorated(v: int) -> str:
    """Return a str."""
    return str(v)


assert_type(decorated, Callable[[int], str])


@m.one.connect(thread="main")  # type: ignore
def wrong(v: str) -> None:
    """Take the wrong type."""


@m.raw.connect(thread="main")
def untyped_options(a: int, b: str, flag: bool = False) -> None:
    """Keep its own signature."""


untyped_options(1, "x", flag=True)
m.raw.connect(on_three)


def on_optional_int(v: int | None) -> None:
    """Take an optional int."""


def on_item_set(key: int, value: str) -> None:
    """Take a key and a value."""


Selection[int]().events.active.connect(on_optional_int)
EventedObjectProxy([1]).events.item_set.connect(on_item_set)
