"""misc utils."""
from contextlib import contextmanager
from functools import partial
from typing import Any, Callable, Iterator, Tuple

from ._signal import SignalInstance

__all__ = ["debug_events"]


def _default_event_logger(event_name: str, args: Tuple[Any, ...]) -> None:
    print(f"{event_name}.emit{args!r}")


@contextmanager
def debug_events(
    obj: Any, logger: Callable[[str, Tuple[Any, ...]], None] = _default_event_logger
) -> Iterator[None]:
    """Context manager to print events emitted SignalInstances on `obj`."""
    disconnectors = []
    for n in dir(obj):
        attr = getattr(obj, n)
        if isinstance(attr, SignalInstance):

            def _report(*args: Any, _n: str = n) -> None:
                logger(_n, args)

            attr.connect(_report)
            disconnectors.append(partial(attr.disconnect, _report))

    try:
        yield
    finally:
        for disconnector in disconnectors:
            disconnector()
