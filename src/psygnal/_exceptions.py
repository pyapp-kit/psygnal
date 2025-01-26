from __future__ import annotations

import inspect
import os
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING

import psygnal

if TYPE_CHECKING:
    from collections.abc import Container, Sequence

    from ._signal import SignalInstance


ROOT = str(Path(psygnal.__file__).parent)


class EmitLoopError(Exception):
    """Error type raised when an exception occurs during a callback."""

    __module__ = "psygnal"

    def __init__(
        self,
        exc: BaseException,
        signal: SignalInstance | None = None,
        recursion_depth: int = 0,
        reemission: str | None = None,
        emit_queue: Sequence[tuple] = (),
    ) -> None:
        # if isinstance(exc, EmitLoopError):
        #     super().__init__("nested EmitLoopError.")
        #     return

        self.__cause__ = exc

        # grab the signal name or repr
        if signal is None:  # pragma: no cover
            sig_name: str = ""
        elif instance := signal.instance:
            inst_class = instance.__class__
            mod = getattr(inst_class, "__module__", "")
            if mod:
                mod += "."
            sig_name = f"{mod}{inst_class.__qualname__}.{signal.name}"
        else:
            sig_name = signal.name

        msg = _build_psygnal_exception_msg(sig_name, exc, recursion_depth)

        # queued emission can be confusing, because the `signal.emit()` call shown
        # in the traceback will not match the emission that actually raised the error.
        if reemission == "queued" and (depth := len(emit_queue) - 1):
            msg += (
                "\nNOTE: reemission is set to 'queued', and this error occurred "
                f"at a queue-depth of {depth}.\nEmitting arguments: {emit_queue[-1]})\n"
            )

        super().__init__(msg)


def _build_psygnal_exception_msg(
    sig_name: str, exc: BaseException, recursion_depth: int
) -> str:
    msg = f"\n\nWhile emitting signal {sig_name!r}, an error occurred in a callback:"
    line = f"\n\n  {exc.__class__.__name__}: {exc}"
    msg += line + "\n  " + "-" * (len(line) - 4)

    if recursion_depth:
        s = "s" if recursion_depth > 1 else ""
        msg += f"\nnested {recursion_depth} level{s} deep"

    # get the first frame in the stack that is not in the psygnal package
    stack = inspect.stack()
    with suppress(Exception):
        emit_frame = next(fi for fi in stack if ROOT not in fi.filename)
        msg += "\n\n  SIGNAL EMISSION: \n"
        with suppress(IndexError):
            back_frame = stack[stack.index(emit_frame) + 1]
            msg += f"    {_fmt_frame(back_frame)}\n"
        msg += f"    {_fmt_frame(emit_frame)}  # <-- SIGNAL WAS EMITTED HERE\n"

    # get the last frame in the traceback, the one that raised the exception
    if tb := exc.__traceback__:
        with suppress(Exception):
            if not (inner := inspect.getinnerframes(tb)):
                return msg  # pragma: no cover

            except_frame = inner[-1]

            # show the immediately connected callback first
            first_cb = next((fi for fi in inner if ROOT not in fi.filename), None)
            if first_cb and first_cb != except_frame:
                num_inner = len(inner) - inner.index(first_cb) - 2
                msg += "\n  CALLBACK CHAIN:\n"
                msg += f"    {_fmt_frame(first_cb, with_context=False)}"
                msg += f"    ... {num_inner} more frames ...\n"

            # Then end with the frame that raised the exception
            msg += f"    {_fmt_frame(except_frame)}  # <-- ERROR OCCURRED HERE \n"
            if flocals := except_frame.frame.f_locals:
                if not os.getenv("PSYGNAL_HIDE_LOCALS"):
                    msg += "\n      Local variables:\n"
                    msg += _fmt_locals(flocals)

    return msg


def _fmt_frame(fi: inspect.FrameInfo, with_context: bool = True) -> str:
    msg = f"{fi.filename}:{fi.lineno} in {fi.function}\n"
    if with_context and (code_ctx := fi.code_context):
        msg += f"      {code_ctx[0].strip()}"
    return msg


def _fmt_locals(
    f_locals: dict, exclude: Container[str] = ("self", "cls"), name_width: int = 20
) -> str:
    lines = []
    for name, value in f_locals.items():
        if name not in exclude:
            val_repr = repr(value)
            if len(val_repr) > 60:
                val_repr = val_repr[:60] + "..."  # pragma: no cover
            lines.append("{:>{}} = {}".format(name, name_width, val_repr))
    return "\n".join(lines)
