from unittest.mock import Mock, call

from psygnal import Signal
from psygnal.utils import monitor_events


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
