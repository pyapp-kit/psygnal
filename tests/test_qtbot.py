"""qtbot should work for testing!"""
import operator

import pytest

from psygnal import Signal

pytest.importorskip("pytestqt")


def is_(*val):
    def _inner(*other):
        return operator.eq(other, val)

    return _inner


def test_wait_signals(qtbot):
    class Emitter:
        sig1 = Signal()
        sig2 = Signal(int)
        sig3 = Signal(int, int)

    e = Emitter()
    signals = [e.sig1, e.sig2, e.sig3, e.sig1]
    checks = [is_(), is_(1), is_(2, 3), is_()]
    with qtbot.waitSignals(signals, check_params_cbs=checks, order="strict"):
        e.sig1.emit()
        e.sig2.emit(1)
        e.sig3.emit(2, 3)
        e.sig1.emit()
