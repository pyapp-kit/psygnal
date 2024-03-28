from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._signal import SignalInstance


class EmitLoopError(Exception):
    """Error type raised when an exception occurs during a callback."""

    __module__ = "psygnal"

    def __init__(
        self,
        exc: BaseException,
        signal: SignalInstance | None = None,
    ) -> None:
        self.__cause__ = exc  # mypyc doesn't set this, but uncompiled code would

        if signal is None:  # pragma: no cover
            sig_name = ""
        else:
            if instsance := signal.instance:
                inst_class = instsance.__class__
                mod = getattr(inst_class, "__module__", "")
                if mod:
                    mod += "."
                sig_name = f"{mod}{inst_class.__qualname__}.{signal.name}"
            else:
                sig_name = repr(signal)

        msg = f"\n\nWhile emitting signal {sig_name!r}, an error occurred in a callback"
        if tb := exc.__traceback__:
            while tb and tb.tb_next is not None:
                tb = tb.tb_next
            frame = tb.tb_frame
            filename = frame.f_code.co_filename
            func_name = getattr(frame.f_code, "co_qualname", frame.f_code.co_name)
            msg += f":\n  File {filename}:{frame.f_lineno}, in {func_name}\n"
            if frame.f_locals:
                msg += "  With local variables:\n"
                for name, value in frame.f_locals.items():
                    msg += f"    {name} = {value!r}\n"

        msg += f"\nSee {exc.__class__.__name__} above for details."
        super().__init__(msg)
