"""These utilities may help when using signals and evented objects."""

from contextlib import contextmanager
from functools import partial
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Tuple

from ._signal import SignalInstance

__all__ = ["monitor_events", "iter_signal_instances"]


def _default_event_monitor(signal_name: str, args: Tuple[Any, ...]) -> None:
    print(f"{signal_name}.emit{args!r}")


@contextmanager
def monitor_events(
    obj: Any,
    logger: Callable[[str, Tuple[Any, ...]], Any] = _default_event_monitor,
    include_private_attrs: bool = False,
) -> Iterator[None]:
    """Context manager to print or collect events emitted by SignalInstances on `obj`.

    Parameters
    ----------
    obj : object
        Any object that has an attribute that has a SignalInstance (or SignalGroup).
    logger : Callable[[str, Tuple[Any, ...]], None], optional
        A optional function to handle the logging of the event emission.  This function
        must take two positional args: a signal name string, and a tuple that contains
        the emitted arguments. The default logger simply prints the signal name and
        emitted args.
    include_private_attrs : bool
        Whether private signals (starting with an underscore) should also be logged,
        by default False
    """
    disconnectors = []
    for siginst in iter_signal_instances(obj, include_private_attrs):

        def _report(*args: Any, signal_name: str = siginst.name) -> None:
            logger(signal_name, args)

        siginst.connect(_report)
        disconnectors.append(partial(siginst.disconnect, _report))

    try:
        yield
    finally:
        for disconnector in disconnectors:
            disconnector()


def iter_signal_instances(
    obj: Any, include_private_attrs: bool = False
) -> Iterable[SignalInstance]:
    """Yield all `SignalInstance` attributes found on `obj`.

    Parameters
    ----------
    obj : object
        Any object that has an attribute that has a SignalInstance (or SignalGroup).
    include_private_attrs : bool
        Whether private signals (starting with an underscore) should also be logged,
        by default False

    Yields
    ------
    SignalInstance
        SignalInstances (and SignalGroups) found as attributes on `obj`.
    """
    for n in dir(obj):
        if include_private_attrs or not n.startswith("_"):
            attr = getattr(obj, n)
            if isinstance(attr, SignalInstance):
                yield attr


_COMPILED_EXTS = (".so", ".pyd")
_BAK = "_BAK"


def decompile() -> None:
    """Mangle names of mypyc-compiled files so that they aren't used.

    This function requires write permissions to the psygnal source directory.
    """
    for suffix in _COMPILED_EXTS:
        for path in Path(__file__).parent.rglob(f"**/*{suffix}"):
            path.rename(path.with_suffix(f"{suffix}{_BAK}"))


def recompile() -> None:
    """Fix all name-mangled mypyc-compiled files so that they ARE used.

    This function requires write permissions to the psygnal source directory.
    """
    for suffix in _COMPILED_EXTS:
        for path in Path(__file__).parent.rglob(f"**/*{suffix}{_BAK}"):
            path.rename(path.with_suffix(suffix))
