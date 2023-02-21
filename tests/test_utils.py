import os
import sys
from pathlib import Path
from unittest.mock import Mock, call

import pytest

from psygnal import Signal
from psygnal.utils import decompile, monitor_events, recompile


def test_event_debugger(capsys):
    """Test that the event debugger works"""

    class M:
        sig = Signal(int, int)

    m = M()
    _logger = Mock()

    assert not m.sig._slots

    with monitor_events(m, _logger):
        assert len(m.sig._slots) == 1
        m.sig.emit(1, 2)
        m.sig.emit(3, 4)

    assert _logger.call_count == 2
    _logger.assert_has_calls([call("sig", (1, 2)), call("sig", (3, 4))])
    assert not m.sig._slots

    with monitor_events(m):
        m.sig.emit(1, 2)
        m.sig.emit(3, 4)

    captured = capsys.readouterr()
    assert captured.out == "sig.emit(1, 2)\nsig.emit(3, 4)\n"


OLD_WIN = bool((sys.version_info < (3, 8)) and os.name == "nt")


@pytest.mark.skipif(OLD_WIN, reason="can't rewrite open files on Windows")
def test_decompile_recompile(monkeypatch):
    import psygnal

    was_compiled = psygnal._compiled

    decompile()
    monkeypatch.delitem(sys.modules, "psygnal")
    monkeypatch.delitem(sys.modules, "psygnal._signal")
    import psygnal

    assert not psygnal._compiled

    if was_compiled:
        assert list(Path(psygnal.__file__).parent.rglob("**/*_BAK"))
        recompile()
        monkeypatch.delitem(sys.modules, "psygnal")
        monkeypatch.delitem(sys.modules, "psygnal._signal")
        import psygnal

        assert psygnal._compiled


def test_debug_import(monkeypatch):
    """Test that PSYGNAL_UNCOMPILED gives a warning."""
    monkeypatch.delitem(sys.modules, "psygnal")
    monkeypatch.setenv("PSYGNAL_UNCOMPILED", "1")

    with pytest.warns(UserWarning, match="PSYGNAL_UNCOMPILED no longer has any effect"):
        import psygnal  # noqa: F401
