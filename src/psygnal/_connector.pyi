"""Protocols for the decorator that `SignalInstance.connect` returns."""

import threading
from collections.abc import Callable
from typing import Any, Literal, Protocol, TypedDict, TypeVar, TypeVarTuple, overload

from ._signal import ReemissionVal, SignalInstance
from ._weak_callback import RefErrorChoice

T1 = TypeVar("T1")
T2 = TypeVar("T2")
T3 = TypeVar("T3")
T4 = TypeVar("T4")
T5 = TypeVar("T5")
R = TypeVar("R")
Ts = TypeVarTuple("Ts")

class SignalKwargs(TypedDict, total=False):
    description: str
    name: str | None
    check_nargs_on_connect: bool
    check_types_on_connect: bool
    reemission: ReemissionVal
    signal_instance_class: type[SignalInstance] | None

class ConnectKwargs(TypedDict, total=False):
    thread: threading.Thread | Literal["main", "current"] | None
    check_nargs: bool | None
    check_types: bool | None
    unique: bool | Literal["raise"]
    max_args: int | None
    on_ref_error: RefErrorChoice
    priority: int
    emit_on_evented_child_events: bool

class Connector(Protocol[*Ts]):
    @overload
    def __call__(
        self,
        slot: Callable[[], R],
        /,
    ) -> Callable[[], R]: ...
    @overload
    def __call__(
        self: Connector[T1, *tuple[Any, ...]],
        slot: Callable[[T1], R],
        /,
    ) -> Callable[[T1], R]: ...
    @overload
    def __call__(
        self: Connector[T1, T2, *tuple[Any, ...]],
        slot: Callable[[T1, T2], R],
        /,
    ) -> Callable[[T1, T2], R]: ...
    @overload
    def __call__(
        self: Connector[T1, T2, T3, *tuple[Any, ...]],
        slot: Callable[[T1, T2, T3], R],
        /,
    ) -> Callable[[T1, T2, T3], R]: ...
    @overload
    def __call__(
        self: Connector[T1, T2, T3, T4, *tuple[Any, ...]],
        slot: Callable[[T1, T2, T3, T4], R],
        /,
    ) -> Callable[[T1, T2, T3, T4], R]: ...
    @overload
    def __call__(
        self: Connector[T1, T2, T3, T4, T5, *tuple[Any, ...]],
        slot: Callable[[T1, T2, T3, T4, T5], R],
        /,
    ) -> Callable[[T1, T2, T3, T4, T5], R]: ...
