from unittest.mock import Mock, call

import pytest

from psygnal import EmissionInfo, Signal
from psygnal.utils import monitor_events


def test_event_debugger(capsys) -> None:
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
    _logger.assert_has_calls(
        [call(EmissionInfo(m.sig, (1, 2))), call(EmissionInfo(m.sig, (3, 4)))]
    )
    assert not m.sig._slots

    with monitor_events(m):
        m.sig.emit(1, 2)
        m.sig.emit(3, 4)

    captured = capsys.readouterr()
    assert captured.out == "sig.emit(1, 2)\nsig.emit(3, 4)\n"


def test_old_monitor_api_dep_warning() -> None:
    class M:
        sig = Signal(int, int)

    mock = Mock()

    def _monitor(signal_name: str, args: tuple) -> None:
        mock(signal_name, args)

    m = M()
    with pytest.warns(
        UserWarning, match="logger functions must now take a single argument"
    ):
        with monitor_events(m, logger=_monitor):  # type: ignore
            m.sig.emit(1, 2)
    mock.assert_called_once_with("sig", (1, 2))

    with pytest.raises(ValueError, match="logger function must take a single argument"):
        with monitor_events(logger=_monitor):  # type: ignore
            m.sig.emit(1, 2)

    mock.reset_mock()
    with monitor_events(m, logger=mock):
        m.sig.emit(1, 2)
    mock.assert_called_once_with(EmissionInfo(m.sig, (1, 2)))

    # global monitor
    mock.reset_mock()
    with monitor_events(logger=mock):
        m.sig.emit(1, 2)
    mock.assert_called_once_with(EmissionInfo(m.sig, (1, 2)))


def test_monitor_all() -> None:
    class M:
        sig = Signal(int, int)

    m1 = M()
    m2 = M()
    _logger = Mock()

    with monitor_events(logger=_logger):
        m1.sig.emit(1, 2)
        m2.sig.emit(3, 4)
        m1.sig.emit(5, 6)
        m2.sig.emit(7, 8)

    assert _logger.call_args_list == [
        call(EmissionInfo(m1.sig, (1, 2))),
        call(EmissionInfo(m2.sig, (3, 4))),
        call(EmissionInfo(m1.sig, (5, 6))),
        call(EmissionInfo(m2.sig, (7, 8))),
    ]
