from __future__ import annotations

import inspect
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any

import psygnal

if TYPE_CHECKING:
    from ._signal import SignalInstance


ROOT = str(Path(psygnal.__file__).parent)


class EmitLoopError(Exception):
    """Error type raised when an exception occurs during a callback."""

    __module__ = "psygnal"

    def __init__(
        self,
        exc: BaseException,
        signal: SignalInstance | None = None,
    ) -> None:
        self.__cause__ = exc

        # grab the signal name or repr
        if signal is None:  # pragma: no cover
            sig_name: Any = ""
        else:
            if instsance := signal.instance:
                inst_class = instsance.__class__
                mod = getattr(inst_class, "__module__", "")
                if mod:
                    mod += "."
                sig_name = f"{mod}{inst_class.__qualname__}.{signal.name}"
            else:
                sig_name = signal

        etype = exc.__class__.__name__  # name of the exception raised by callback.
        msg = (
            f"\n\nWhile emitting signal {sig_name!r}, a {etype} occurred in a callback"
        )
        if tb := exc.__traceback__:
            msg += ":\n"

            # get the first frame in the stack that is not in the psygnal package
            with suppress(Exception):
                fi = next(fi for fi in inspect.stack() if ROOT not in fi.filename)
                msg += f"\n  Signal emitted at: {fi.filename}:{fi.lineno}, in {fi.function}\n"  # noqa: E501
                if fi.code_context:
                    msg += f"    >  {fi.code_context[0].strip()}\n"

            # get the last frame in the traceback, the one that raised the exception
            with suppress(Exception):
                fi = inspect.getinnerframes(tb)[-1]
                msg += f"\n  Callback error at: {fi.filename}:{fi.lineno}, in {fi.function}\n"  # noqa: E501
                if fi.code_context:
                    msg += f"    >  {fi.code_context[0].strip()}\n"
                if flocals := fi.frame.f_locals:
                    msg += "    Local variables:\n"
                    for name, value in flocals.items():
                        if name not in ("self", "cls"):
                            msg += f"       {name} = {value!r}\n"

        msg += f"\nSee {etype} above for original traceback."
        super().__init__(msg)
