"""qtbot should work for testing!"""
import pytest

from psygnal import Signal
from psygnal._signal import _guess_qtsignal_signature

pytest.importorskip("pytestqt")


def is_(*val):
    def _inner(*other):
        return other == val

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


def test_guess_signal_sig(qtbot):
    from qtpy import QtCore

    class QtObject(QtCore.QObject):
        qsig1 = QtCore.Signal()
        qsig2 = QtCore.Signal(int)
        qsig3 = QtCore.Signal(int, str)

    q_obj = QtObject()
    assert "qsig1()" in _guess_qtsignal_signature(q_obj.qsig1)
    assert "qsig1()" in _guess_qtsignal_signature(q_obj.qsig1.emit)
    assert "qsig2(int)" in _guess_qtsignal_signature(q_obj.qsig2)
    assert "qsig2(int)" in _guess_qtsignal_signature(q_obj.qsig2.emit)
    assert "qsig3(int,QString)" in _guess_qtsignal_signature(q_obj.qsig3)
    assert "qsig3(int,QString)" in _guess_qtsignal_signature(q_obj.qsig3.emit)


def test_connect_qt_signal_instance(qtbot):
    from qtpy import QtCore

    class Emitter:
        sig1 = Signal()
        sig2 = Signal(int)
        sig3 = Signal(int, int)

    class QtObject(QtCore.QObject):
        qsig1 = QtCore.Signal()
        qsig2 = QtCore.Signal(int)

    q_obj = QtObject()
    e = Emitter()

    # the hard case: signal.emit takes less args than we emit
    def test_receives_1(value: int) -> bool:
        # making sure that qsig2.emit only receives and emits 1 value
        return value == 1

    e.sig3.connect(q_obj.qsig2.emit)
    with qtbot.waitSignal(q_obj.qsig2, check_params_cb=test_receives_1):
        e.sig3.emit(1, 2)  # too many

    # the "standard" cases, where params match
    e.sig1.connect(q_obj.qsig1.emit)
    with qtbot.waitSignal(q_obj.qsig1):
        e.sig1.emit()

    e.sig2.connect(q_obj.qsig2.emit)
    with qtbot.waitSignal(q_obj.qsig2):
        e.sig2.emit(1)

    # the flip case: signal.emit takes more args than we emit
    with pytest.raises(ValueError):
        e.sig1.connect(q_obj.qsig2.emit)
    e.sig1.emit()
