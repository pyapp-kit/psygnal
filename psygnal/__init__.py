"""psygnal is a pure-python implementation of Qt-style signals & slots."""
try:
    from ._version import version as __version__
except ImportError:  # pragma: no cover
    __version__ = "unknown"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@gmail.com"
__all__ = ["Signal", "SignalInstance", "_compiled", "__version__"]

try:
    import cython
except ImportError:  # pragma: no cover
    _compiled: bool = False
else:  # pragma: no cover
    try:
        _compiled = cython.compiled
    except AttributeError:
        _compiled = False

from ._signal import Signal, SignalInstance
