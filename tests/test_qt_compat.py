"""qtbot should work for testing!"""
from typing import TYPE_CHECKING, Any, Callable, Tuple

import pytest

from psygnal import Signal
from psygnal._signal import _guess_qtsignal_signature

pytest.importorskip("pytestqt")
if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


def _equals(*val: Any) -> Callable[[Tuple[Any, ...]], bool]:
    def _inner(*other: Any) -> bool:
        return other == val

    return _inner


def test_wait_signals(qtbot: "QtBot") -> None:
    class Emitter:
        sig1 = Signal()
        sig2 = Signal(int)
        sig3 = Signal(int, int)

    e = Emitter()

    with qtbot.waitSignal(e.sig2, check_params_cb=_equals(1)):
        e.sig2.emit(1)

    with qtbot.waitSignal(e.sig3, check_params_cb=_equals(2, 3)):
        e.sig3.emit(2, 3)

    with qtbot.waitSignals([e.sig3], check_params_cbs=[_equals(2, 3)]):
        e.sig3.emit(2, 3)

    signals = [e.sig1, e.sig2, e.sig3, e.sig1]
    checks = [_equals(), _equals(1), _equals(2, 3), _equals()]
    with qtbot.waitSignals(signals, check_params_cbs=checks, order="strict"):
        e.sig1.emit()
        e.sig2.emit(1)
        e.sig3.emit(2, 3)
        e.sig1.emit()


def test_guess_signal_sig(qtbot: "QtBot") -> None:
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


def test_connect_qt_signal_instance(qtbot: "QtBot") -> None:
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
