from __future__ import annotations

from threading import Timer
from typing import TYPE_CHECKING, Any, Callable, Optional, Union, overload

if TYPE_CHECKING:
    from typing_extensions import Literal, ParamSpec

    P = ParamSpec("P")

    Kind = Literal["throttler", "debouncer"]
    EmissionPolicy = Literal["trailing", "leading"]


class _ThrottlerBase:
    _timer: Timer

    def __init__(
        self,
        func: Callable[P, Any],
        interval: int = 100,
        policy: EmissionPolicy = "leading",
    ) -> None:
        self._func = func
        self._interval = interval
        self._policy = policy
        self._has_pending = False
        self._timer = Timer(0, lambda: None)
        self._timer.start()

    def _actually_call(self) -> None:
        self._has_pending = False
        self._func(*self._args, **self._kwargs)  # type: ignore
        self._start_timer()

    def _call_if_has_pending(self) -> None:
        if self._has_pending:
            self._actually_call()

    def _start_timer(self) -> None:
        self._timer.cancel()
        self._timer = Timer(self._interval / 1000, self._call_if_has_pending)
        self._timer.start()

    def cancel(self) -> None:
        """Cancel any pending calls."""
        self._has_pending = False
        self._timer.cancel()

    def flush(self) -> None:
        """Force a call if there is one pending."""
        self._call_if_has_pending()


class Throttler(_ThrottlerBase):
    """Class that prevents calling `func` more than once per `interval`.

    Parameters
    ----------
    func : Callable[P, Any]
        a function to wrap
    interval : int, optional
        the minimum interval in ms that must pass before the function is called again,
        by default 100
    policy : EmissionPolicy, optional
        Whether to invoke the function on the "leading" or "trailing" edge of the
        wait timer, by default "leading"
    """

    _timer: Timer

    def __init__(
        self,
        func: Callable[..., Any],
        interval: int = 100,
        policy: EmissionPolicy = "leading",
    ) -> None:

        super().__init__(func, interval, policy)

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        """Call underlying function."""
        self._has_pending = True
        self._args = args
        self._kwargs = kwargs

        if not self._timer.is_alive():
            if self._policy == "leading":
                self._actually_call()
            else:
                self._start_timer()


class Debouncer(_ThrottlerBase):
    """Class that waits at least `interval` before calling `func`.

    Parameters
    ----------
    func : Callable[P, Any]
        a function to wrap
    interval : int, optional
        the minimum interval in ms that must pass before the function is called again,
        by default 100
    policy : EmissionPolicy, optional
        Whether to invoke the function on the "leading" or "trailing" edge of the
        wait timer, by default "trailing"
    """

    _timer: Timer

    def __init__(
        self,
        func: Callable[..., Any],
        interval: int = 100,
        policy: EmissionPolicy = "trailing",
    ) -> None:
        super().__init__(func, interval, policy)

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        """Call underlying function."""
        self._has_pending = True
        self._args = args
        self._kwargs = kwargs

        if not self._timer.is_alive() and self._policy == "leading":
            self._actually_call()
        self._start_timer()


@overload
def throttled(
    func: Callable[P, Any],
    timeout: int = 100,
    leading: bool = True,
) -> Callable[P, None]:
    ...


@overload
def throttled(
    func: Literal[None] = None,
    timeout: int = 100,
    leading: bool = True,
) -> Callable[[Callable[P, Any]], Callable[P, None]]:
    ...


def throttled(
    func: Optional[Callable[P, Any]] = None,
    timeout: int = 100,
    leading: bool = True,
) -> Union[Callable[P, None], Callable[[Callable[P, Any]], Callable[P, None]]]:
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

    Examples
    --------
    ```python
    from psygnal import Signal, throttled

    class MyEmitter:
        changed = Signal(int)

    def on_change(val: int)
        # do something possibly expensive
        ...

    emitter = MyEmitter()

    # connect the `on_change` whenever `emitter.changed` is emitted
    # BUT, no more than once every 50 milliseconds
    emitter.changed.connect(throttled(on_change, timeout=50))
    ```
    """

    def deco(func: Callable[P, Any]) -> Callable[P, None]:
        policy: EmissionPolicy = "leading" if leading else "trailing"
        return Throttler(func, timeout, policy)

    return deco(func) if func is not None else deco


@overload
def debounced(
    func: Callable[P, Any],
    timeout: int = 100,
    leading: bool = False,
) -> Callable[P, None]:
    ...


@overload
def debounced(
    func: Literal[None] = None,
    timeout: int = 100,
    leading: bool = False,
) -> Callable[[Callable[P, Any]], Callable[P, None]]:
    ...


def debounced(
    func: Optional[Callable[P, Any]] = None,
    timeout: int = 100,
    leading: bool = False,
) -> Union[Callable[P, None], Callable[[Callable[P, Any]], Callable[P, None]]]:
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

    Examples
    --------
    ```python
    from psygnal import Signal, debounced

    class MyEmitter:
        changed = Signal(int)

    def on_change(val: int)
        # do something possibly expensive
        ...

    emitter = MyEmitter()

    # connect the `on_change` whenever `emitter.changed` is emitted
    # ONLY once at least 50 milliseconds have passed since the last signal emission.
    emitter.changed.connect(debounced(on_change, timeout=50))
    ```
    """

    def deco(func: Callable[P, Any]) -> Callable[P, None]:
        policy: EmissionPolicy = "leading" if leading else "trailing"
        return Debouncer(func, timeout, policy)

    return deco(func) if func is not None else deco
