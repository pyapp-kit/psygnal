"""misc utils."""
from contextlib import contextmanager
from functools import partial
from typing import Any, Callable, Iterator

from ._signal import SignalInstance


@contextmanager
def debug_events(obj: Any, logger: Callable[[str], None] = print) -> Iterator[None]:
    """Context manager to print events emitted SignalInstances on `obj`."""
    disconnectors = []
    for n in dir(obj):
        attr = getattr(obj, n)
        if isinstance(attr, SignalInstance):

            def _report(*args: Any, _n: str = n) -> None:
                msg = f"{_n}.emit{args!r}"
                logger(msg)

            attr.connect(_report)
            disconnectors.append(partial(attr.disconnect, _report))

    try:
        yield
    finally:
        for disconnector in disconnectors:
            disconnector()
