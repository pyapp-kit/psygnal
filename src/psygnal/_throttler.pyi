# this pyi file exists until we can use ParamSpec with mypyc in the main file.
from collections.abc import Callable
from typing import Any, Generic, Literal, ParamSpec, overload

P = ParamSpec("P")

Kind = Literal["throttler", "debouncer"]
EmissionPolicy = Literal["trailing", "leading"]

class _ThrottlerBase(Generic[P]):
    def __init__(
        self,
        func: Callable[P, Any],
        interval: int = 100,
        policy: EmissionPolicy = "leading",
    ) -> None: ...
    def cancel(self) -> None:
        """Cancel any pending calls."""

    def flush(self) -> None:
        """Force a call if there is one pending."""

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> None: ...

class Throttler(_ThrottlerBase[P]):
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

class Debouncer(_ThrottlerBase[P]):
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

@overload
def throttled(
    func: Callable[P, Any],
    timeout: int = 100,
    leading: bool = True,
) -> Throttler[P]: ...
@overload
def throttled(
    func: Literal[None] | None = None,
    timeout: int = 100,
    leading: bool = True,
) -> Callable[[Callable[P, Any]], Throttler[P]]: ...
@overload
def debounced(
    func: Callable[P, Any],
    timeout: int = 100,
    leading: bool = False,
) -> Debouncer[P]: ...
@overload
def debounced(
    func: Literal[None] | None = None,
    timeout: int = 100,
    leading: bool = False,
) -> Callable[[Callable[P, Any]], Debouncer[P]]: ...
