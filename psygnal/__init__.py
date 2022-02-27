"""psygnal is a pure-python implementation of Qt-style signals & slots."""
try:
    from ._version import version as __version__
except ImportError:  # pragma: no cover
    __version__ = "unknown"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@gmail.com"
__all__ = [
    "__version__",
    "_compiled",
    "EmissionInfo",
    "Signal",
    "SignalGroup",
    "SignalInstance",
    "throttled",
    "debounced",
    "SignalThrottler",
    "SignalDebouncer",
]
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

    from . import _group, _signal

    Signal = _signal.Signal
    SignalInstance = _signal.SignalInstance
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
    m = _import_purepy_mod("_group")
    SignalGroup, EmissionInfo = m.SignalGroup, m.EmissionInfo
    m = _import_purepy_mod("_throttler")
    throttled, debounced = m.throttled, m.debounced
    del _import_purepy_mod

else:
    from ._group import EmissionInfo, SignalGroup
    from ._signal import Signal, SignalInstance, _compiled
    from ._throttler import debounced, throttled

del os, TYPE_CHECKING
