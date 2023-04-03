from __future__ import annotations

from threading import current_thread

try:
    from qtpy.QtCore import Qt, QTimer
except ImportError:
    raise ImportError(
        "The psygnal.qt module requires qtpy and some Qt backend to be installed"
    ) from None

_TIMER: dict[Tread, QTimer] = {}


def start_emitting_from_queue(
    msec: int = 0, timer_type: Qt.TimerType = Qt.TimerType.PreciseTimer
) -> None:
    """Start a QTimer that will monitor the global emission queue.

    When callbacks are connected to signals with `connect(type='queued')`, then they
    are not invoked immediately, but rather added to a global queue.  This function
    starts a QTimer that will periodically check the queue and invoke any callbacks
    that are waiting to be invoked (in whatever thread this QTimer is running in).
    """
    thread = current_thread()
    if thread not in _TIMER:
        _TIMER[thread] = QTimer()
        from ._queue import emit_queued

        _TIMER[thread].timeout.connect(emit_queued)

    _TIMER[thread].setTimerType(timer_type)
    if _TIMER[thread].isActive():
        _TIMER[thread].setInterval(msec)
    else:
        _TIMER[thread].start(msec)


def stop_emitting_from_queue() -> None:
    """Stop the QTimer that monitors the global emission queue."""
    global _TIMER
    timer = _TIMER.get(current_thread())
    if timer is not None:
        timer.stop()
