from __future__ import annotations

from concurrent.futures import Future
from functools import wraps
from threading import Timer
from typing import TYPE_CHECKING, overload

from ._signal import Signal

if TYPE_CHECKING:
    import sys
    from typing import Callable, Generic, Optional, TypeVar, Union

    from typing_extensions import Literal, ParamSpec, Protocol

    from ._signal import SignalInstance

    P = ParamSpec("P")
    R = TypeVar("R")

    class _ThrottledCallable(Generic[P, R], Protocol):
        triggered: SignalInstance

        def cancel(self) -> None:
            ...

        def flush(self) -> None:
            ...

        def set_timeout(self, timeout: int) -> None:
            ...

        if sys.version_info < (3, 9):

            def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Future:
                ...

        else:

            def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Future[R]:
                ...

    Kind = Literal["throttler", "debouncer"]
    EmissionPolicy = Literal["trailing", "leading"]


class _GenericSignalThrottler:

    triggered = Signal()
    timeoutChanged = Signal(int)

    def __init__(
        self, kind: Kind, emissionPolicy: EmissionPolicy, timeout: int = 1
    ) -> None:

        self.kind = kind
        self.emission_policy = emissionPolicy
        self._hasPendingEmission = False
        self._timeout: int = timeout  # ms
        self._timer: Optional[Timer] = None

    @property
    def timeout(self) -> int:
        """Return current timeout in milliseconds."""
        return self._timeout

    @timeout.setter
    def timeout(self, timeout: int) -> None:
        """Set timeout in milliseconds."""
        if self._timeout != timeout:
            self._timeout = timeout
            self.timeoutChanged.emit(timeout)

    def throttle(self) -> None:
        """Emit triggered if not running, then start timer."""
        # public slot
        self._hasPendingEmission = True
        # Emit only if we haven't emitted already. We know if that's
        # the case by checking if the timer is running.
        if self.emission_policy == "leading" and not (
            self._timer and self._timer.is_alive()
        ):
            self._emitTriggered()

        # The timer is started in all cases. If we got a signal, and we're Leading,
        # and we did emit because of that, then we don't re-emit when the timer fires
        # (unless we get ANOTHER signal).
        if self.kind == "throttler":  # sourcery skip: merge-duplicate-blocks
            if not (self._timer and self._timer.is_alive()):
                self._start_timer()  # actual start, not restart
        elif self.kind == "debouncer":
            self._start_timer()  # restart

        assert self._timer and self._timer.is_alive()

    def _start_timer(self) -> None:
        if self._timer and self._timer.is_alive():
            self._timer.cancel()
        self._timer = Timer(self._timeout / 1000, self._maybeEmitTriggered)
        self._timer.start()

    def cancel(self) -> None:
        """Cancel any pending emissions."""
        self._hasPendingEmission = False

    def flush(self) -> None:
        """Force emission of any pending emissions."""
        self._maybeEmitTriggered()

    def _emitTriggered(self) -> None:
        self._hasPendingEmission = False
        self.triggered.emit()
        self._start_timer()

    def _maybeEmitTriggered(self) -> None:
        if self._hasPendingEmission:
            self._emitTriggered()


# ### Convenience classes ###


class SignalThrottler(_GenericSignalThrottler):
    """A Signal Throttler.

    This object's `triggered` signal will emit at most once per timeout
    (set with setTimeout()).
    """

    def __init__(self, policy: EmissionPolicy = "leading") -> None:
        super().__init__("throttler", policy)


class SignalDebouncer(_GenericSignalThrottler):
    """A Signal Debouncer.

    This object's `triggered` signal will not be emitted until `self.timeout()`
    milliseconds have elapsed since the last time `triggered` was emitted.
    """

    def __init__(self, policy: EmissionPolicy = "trailing") -> None:
        super().__init__("debouncer", policy)


@overload
def throttled(
    func: Callable[P, R],
    timeout: int = 100,
    leading: bool = True,
) -> _ThrottledCallable[P, R]:
    ...


@overload
def throttled(
    func: Literal[None] = None,
    timeout: int = 100,
    leading: bool = True,
) -> Callable[[Callable[P, R]], _ThrottledCallable[P, R]]:
    ...


def throttled(  # type: ignore [misc]
    func: Optional[Callable[P, R]] = None,
    timeout: int = 100,
    leading: bool = True,
) -> Union[
    _ThrottledCallable[P, R], Callable[[Callable[P, R]], _ThrottledCallable[P, R]]
]:
    """Create a throttled function that invokes func at most once per timeout.

    The throttled function comes with a `cancel` method to cancel delayed func
    invocations and a `flush` method to immediately invoke them. Options
    to indicate whether func should be invoked on the leading and/or trailing
    edge of the wait timeout. The func is invoked with the last arguments provided
    to the throttled function. Subsequent calls to the throttled function return
    the result of the last func invocation.

    This decorator may be used with or without parameters.

    Parameters
    ----------
    func : Callable
        A function to throttle
    timeout : int
        Timeout in milliseconds to wait before allowing another call, by default 100
    leading : bool
        Whether to invoke the function on the leading edge of the wait timer,
        by default True
    """
    return _make_decorator(func, timeout, leading, "throttler")  # type: ignore


@overload
def debounced(
    func: Callable[P, R],
    timeout: int = 100,
    leading: bool = False,
) -> _ThrottledCallable[P, R]:
    ...


@overload
def debounced(
    func: Literal[None] = None,
    timeout: int = 100,
    leading: bool = False,
) -> Callable[[Callable[P, R]], _ThrottledCallable[P, R]]:
    ...


def debounced(  # type: ignore [misc]
    func: Optional[Callable[P, R]] = None,
    timeout: int = 100,
    leading: bool = False,
) -> Union[
    _ThrottledCallable[P, R], Callable[[Callable[P, R]], _ThrottledCallable[P, R]]
]:
    """Create a debounced function that delays invoking `func`.

    `func` will not be invoked until `timeout` ms have elapsed since the last time
    the debounced function was invoked.

    The debounced function comes with a `cancel` method to cancel delayed func
    invocations and a `flush` method to immediately invoke them. Options
    indicate whether func should be invoked on the leading and/or trailing edge
    of the wait timeout. The func is invoked with the *last* arguments provided to
    the debounced function. Subsequent calls to the debounced function return the
    result of the last `func` invocation.

    This decorator may be used with or without parameters.

    Parameters
    ----------
    func : Callable
        A function to throttle
    timeout : int
        Timeout in milliseconds to wait before allowing another call, by default 100
    leading : bool
        Whether to invoke the function on the leading edge of the wait timer,
        by default False
    """
    return _make_decorator(func, timeout, leading, "debouncer")  # type: ignore


def _make_decorator(
    func: Optional[Callable[P, R]],
    timeout: int,
    leading: bool,
    kind: Kind,
) -> Union[
    _ThrottledCallable[P, R], Callable[[Callable[P, R]], _ThrottledCallable[P, R]]
]:
    def deco(func: Callable[P, R]) -> _ThrottledCallable[P, R]:
        policy: EmissionPolicy = "leading" if leading else "trailing"
        throttle = _GenericSignalThrottler(kind, policy, timeout)
        last_f: Optional[Callable] = None
        future: Optional[Future] = None

        @wraps(func)
        def inner(*args: P.args, **kwargs: P.kwargs) -> Future[R]:
            nonlocal last_f  # type: ignore [misc]
            nonlocal future
            if last_f is not None:
                throttle.triggered.disconnect(last_f)
            if future is not None and not future.done():
                future.cancel()

            future = Future()

            def last_f() -> None:
                future.set_result(func(*args, **kwargs))  # type: ignore [union-attr]

            throttle.triggered.connect(last_f, check_nargs=False)  # type: ignore
            throttle.throttle()
            return future

        setattr(inner, "cancel", throttle.cancel)
        setattr(inner, "flush", throttle.flush)
        setattr(inner, "timeout", throttle.timeout)
        setattr(inner, "triggered", throttle.triggered)
        return inner  # type: ignore

    return deco(func) if func is not None else deco
