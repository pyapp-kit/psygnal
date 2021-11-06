"""psygnal is a pure-python implementation of Qt-style signals & slots."""
try:
    from ._version import version as __version__
except ImportError:  # pragma: no cover
    __version__ = "unknown"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@gmail.com"
__all__ = ["Signal", "SignalInstance", "_compiled", "__version__"]

import os

if os.getenv("PSYGNAL_UNCOMPILED"):
    import importlib.util
    import sys

    MODULE_PATH = os.path.join(os.path.dirname(__file__), "_signal.py")
    spec = importlib.util.spec_from_file_location("_signal", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not find pure python module: {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore
    Signal = module.Signal  # type: ignore
    SignalInstance = module.SignalInstance  # type: ignore
    _compiled = module._compiled  # type: ignore
else:
    from ._signal import Signal, SignalInstance, _compiled

del os
