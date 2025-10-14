"""These utilities may help when using signals and evented objects."""

from __future__ import annotations

from contextlib import contextmanager, suppress
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any
from warnings import warn

from ._group import EmissionInfo, SignalGroup
from ._signal import SignalInstance

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterator

__all__ = ["iter_signal_instances", "monitor_events"]


def _default_event_monitor(info: EmissionInfo) -> None:
    print(f"{info.signal.name}.emit{info.args!r}")


@contextmanager
def monitor_events(
    obj: Any | None = None,
    logger: Callable[[EmissionInfo], Any] = _default_event_monitor,
    include_private_attrs: bool = False,
) -> Iterator[None]:
    """Context manager to print or collect events emitted by SignalInstances on `obj`.

    Parameters
    ----------
    obj : object, optional
        Any object that has an attribute that has a SignalInstance (or SignalGroup).
        If None, all SignalInstances will be monitored.
    logger : Callable[[EmissionInfo], None], optional
        A optional function to handle the logging of the event emission.  This function
        must take two positional args: a signal name string, and a tuple that contains
        the emitted arguments. The default logger simply prints the signal name and
        emitted args.
    include_private_attrs : bool
        Whether private signals (starting with an underscore) should also be logged,
        by default False
    """
    code = getattr(logger, "__code__", None)
    _old_api = bool(code and code.co_argcount > 1)

    if obj is None:
        # install the hook globally
        if _old_api:
            raise ValueError(
                "logger function must take a single argument (an EmissionInfo instance)"
            )
        before, SignalInstance._debug_hook = SignalInstance._debug_hook, logger
    else:
        if _old_api:
            warn(
                "logger functions must now take a single argument (an instance of "
                "psygnal.EmissionInfo). Please update your logger function.",
                stacklevel=2,
            )
        disconnectors = set()
        for siginst in iter_signal_instances(obj, include_private_attrs):
            if _old_api:

                def _report(*args: Any, signal: SignalInstance = siginst) -> None:
                    logger(signal.name, args)  # type: ignore

            else:

                def _report(*args: Any, signal: SignalInstance = siginst) -> None:
                    logger(EmissionInfo(signal, args))

            disconnectors.add(partial(siginst.disconnect, siginst.connect(_report)))

    try:
        yield
    finally:
        if obj is None:
            SignalInstance._debug_hook = before
        else:
            for disconnector in disconnectors:
                disconnector()


def iter_signal_instances(
    obj: Any, include_private_attrs: bool = False
) -> Generator[SignalInstance, None, None]:
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
    # SignalGroup
    if isinstance(obj, SignalGroup):
        for sig in obj:
            yield obj[sig]
        return

    # Signal attached to Class
    for n in dir(obj):
        if not include_private_attrs and n.startswith("_"):
            continue
        with suppress(Exception):  # if we can't access the attribute, skip it
            attr = getattr(obj, n)
            if isinstance(attr, SignalInstance):
                yield attr
            if isinstance(attr, SignalGroup):
                yield attr._psygnal_relay


_COMPILED_EXTS = (".so", ".pyd")
_BAK = "_BAK"


def decompile() -> None:
    """Mangle names of mypyc-compiled files so that they aren't used.

    This function requires write permissions to the psygnal source directory.
    """
    for suffix in _COMPILED_EXTS:  # pragma: no cover
        for path in Path(__file__).parent.rglob(f"**/*{suffix}"):
            path.rename(path.with_suffix(f"{suffix}{_BAK}"))


def recompile() -> None:
    """Fix all name-mangled mypyc-compiled files so that they ARE used.

    This function requires write permissions to the psygnal source directory.
    """
    for suffix in _COMPILED_EXTS:  # pragma: no cover
        for path in Path(__file__).parent.rglob(f"**/*{suffix}{_BAK}"):
            path.rename(path.with_suffix(suffix))
