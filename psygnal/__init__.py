"""psygnal is a pure-python implementation of Qt-style signals & slots."""
try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@gmail.com"
__all__ = ["Signal", "SignalInstance"]

from ._signal import Signal, SignalInstance
