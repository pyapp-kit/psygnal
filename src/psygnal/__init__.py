"""Psygnal implements the observer pattern for Python.

It emulates the signal/slot pattern from Qt, but it does not require Qt.
"""

import os
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ._evented_model import EventedModel  # noqa: TCH004


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
    "emit_queued",
    "EmitLoopError",
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
from ._group_descriptor import SignalGroupDescriptor, get_evented_namespace, is_evented
from ._queue import emit_queued
from ._signal import Signal, SignalInstance, _compiled
from ._throttler import debounced, throttled


def __getattr__(name: str) -> Any:  # pragma: no cover
    if name == "EventedModel":
        from ._evented_model import EventedModel

        return EventedModel
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


del os, TYPE_CHECKING
