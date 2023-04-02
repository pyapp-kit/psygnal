from __future__ import annotations

try:
    from qtpy.QtCore import Qt, QTimer
except ImportError:
    raise ImportError(
        "The psygnal.qt module requires qtpy and some Qt backend to be installed"
    ) from None

_TIMER: QTimer | None = None


def start_emitting_from_queue(
    msec: int = 0, timer_type: Qt.TimerType = Qt.TimerType.PreciseTimer
) -> None:
    """Start a QTimer that will monitor the global emission queue.

    When callbacks are connected to signals with `connect(type='queued')`, then they
    are not invoked immediately, but rather added to a global queue.  This function
    starts a QTimer that will periodically check the queue and invoke any callbacks
    that are waiting to be invoked (in whatever thread this QTimer is running in).
    """
    global _TIMER

    if _TIMER is None:
        _TIMER = QTimer()
        from ._queue import emit_queued

        _TIMER.timeout.connect(emit_queued)

    _TIMER.setTimerType(timer_type)
    if _TIMER.isActive():
        _TIMER.setInterval(msec)
    else:
        _TIMER.start(msec)


def stop_emitting_from_queue() -> None:
    """Stop the QTimer that monitors the global emission queue."""
    global _TIMER
    if _TIMER is not None:
        _TIMER.stop()
