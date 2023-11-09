from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from ._weak_callback import WeakCallback

if TYPE_CHECKING:
    from ._signal import SignalInstance

MSG = """
While emitting signal {sig!r}, an error occurred in callback {cb!r}.
The args passed to the callback were: {args!r}
This is not a bug in psygnal.  See {err!r} above for details.
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
            inst_class = signal.instance.__class__
            mod = getattr(inst_class, "__module__", "")
            sig_name = f"{mod}.{inst_class.__qualname__}.{signal.name}"
        if isinstance(cb, WeakCallback):
            cb_name = cb.slot_repr()
        else:
            cb_name = getattr(cb, "__qualname__", repr(cb))
        super().__init__(
            MSG.format(
                sig=sig_name,
                cb=cb_name,
                args=args,
                err=exc.__class__.__name__,
            )
        )
