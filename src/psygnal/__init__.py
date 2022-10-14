"""psygnal is a pure-python implementation of Qt-style signals & slots."""
try:
    from importlib.metadata import PackageNotFoundError, version
except ImportError:
    from importlib_metadata import PackageNotFoundError, version  # type: ignore

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
    "evented",
    "EventedModel",
    "Signal",
    "SignalGroup",
    "SignalInstance",
    "throttled",
]
import os
from typing import TYPE_CHECKING, Any

from ._evented_decorator import evented

if TYPE_CHECKING:
    from types import ModuleType

    from . import _group, _signal
    from ._evented_model import EventedModel

    Signal = _signal.Signal
    SignalInstance = _signal.SignalInstance
    EmitLoopError = _signal.EmitLoopError
    _compiled = _signal._compiled
    SignalGroup = _group.SignalGroup
    EmissionInfo = _group.EmissionInfo


if os.getenv("PSYGNAL_UNCOMPILED"):

    def _import_purepy_mod(name: str) -> "ModuleType":
        """Import stuff from the uncompiled python module, for debugging."""
        import importlib.util
        import os
        import sys

        ROOT = os.path.dirname(__file__)
        MODULE_PATH = os.path.join(ROOT, f"{name}.py")
        spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
        if spec is None or spec.loader is None:  # pragma: no cover
            raise ImportError(f"Could not find pure python module: {MODULE_PATH}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    m = _import_purepy_mod("_signal")
    Signal, SignalInstance, _compiled = m.Signal, m.SignalInstance, m._compiled
    EmitLoopError = m.EmitLoopError  # type: ignore
    m = _import_purepy_mod("_group")
    SignalGroup, EmissionInfo = m.SignalGroup, m.EmissionInfo
    m = _import_purepy_mod("_throttler")
    throttled, debounced = m.throttled, m.debounced
    del _import_purepy_mod

else:
    from ._group import EmissionInfo, SignalGroup
    from ._signal import EmitLoopError, Signal, SignalInstance, _compiled
    from ._throttler import debounced, throttled


def __getattr__(name: str) -> Any:
    if name == "EventedModel":
        from ._evented_model import EventedModel

        return EventedModel
    raise AttributeError(  # pragma: no cover
        f"module {__name__!r} has no attribute {name!r}"
    )


del os, TYPE_CHECKING
