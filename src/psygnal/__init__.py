"""Psygnal implements the observer pattern for Python.

It emulates the signal/slot pattern from Qt, but it does not require Qt.
"""

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    PackageNotFoundError = Exception
    from ._evented_model_v1 import EventedModel  # noqa: TCH004

    def version(package: str) -> str:
        """Return version."""

else:
    # hiding this import from type checkers so mypyc can work on both 3.7 and later
    try:
        from importlib.metadata import PackageNotFoundError, version
    except ImportError:
        from importlib_metadata import PackageNotFoundError, version


try:
    __version__ = version("psygnal")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@gmail.com"

__all__ = [
    "__version__",
    "_compiled",
    "debounced",
    "EmissionInfo",
    "EmitLoopError",
    "emit_queued",
    "evented",
    "EventedModel",
    "get_evented_namespace",
    "is_evented",
    "Signal",
    "SignalGroup",
    "SignalGroupDescriptor",
    "SignalInstance",
    "throttled",
]


if os.getenv("PSYGNAL_UNCOMPILED"):
    import warnings

    warnings.warn(
        "PSYGNAL_UNCOMPILED no longer has any effect. If you wish to run psygnal "
        "without compiled files, you can run:\n\n"
        'python -c "import psygnal.utils; psygnal.utils.decompile()"\n\n'
        "(You will need to reinstall psygnal to get the compiled version back.)",
        stacklevel=2,
    )

from ._evented_decorator import evented
from ._exceptions import EmitLoopError
from ._group import EmissionInfo, SignalGroup
from ._group_descriptor import (
    SignalGroupDescriptor,
    get_evented_namespace,
    is_evented,
)
from ._queue import emit_queued
from ._signal import Signal, SignalInstance, _compiled
from ._throttler import debounced, throttled


def __getattr__(name: str) -> Any:
    if name == "EventedModel":
        import pydantic.version

        if pydantic.version.VERSION.startswith("2"):
            from ._evented_model_v2 import EventedModel
        else:
            from ._evented_model_v1 import EventedModel  # type: ignore

        return EventedModel
    raise AttributeError(  # pragma: no cover
        f"module {__name__!r} has no attribute {name!r}"
    )


del os, TYPE_CHECKING
