from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from ._weak_callback import WeakCallback

if TYPE_CHECKING:
    from ._signal import SignalInstance

MSG = """
An error occurred in callback {cb!r} connected to psygnal.SignalInstance {sig!r}.
The args passed to the callback were: {args!r}
This is not a bug in psygnal.  See {err} above for details.
"""


class EmitLoopError(Exception):
    """Error type raised when an exception occurs during a callback."""

    def __init__(
        self,
        cb: WeakCallback | Callable,
        args: tuple,
        exc: BaseException,
        signal: SignalInstance | None = None,
    ) -> None:
        self.exc = exc
        self.args = args
        self.__cause__ = exc  # mypyc doesn't set this, but uncompiled code would
        if signal is None:
            sig_name = ""
        else:
            sig_name = f"{signal.instance.__class__.__qualname__}.{signal.name}"
        if isinstance(cb, WeakCallback):
            cb_name = cb.slot_qualname()
        else:
            cb_name = cb.__qualname__
        super().__init__(
            MSG.format(
                cb=cb_name,
                sig=sig_name,
                args=args,
                err=exc.__class__.__name__,
            )
        )
