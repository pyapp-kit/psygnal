"""Module that provides Qt-specific functionality for psygnal.

This module provides convenience functions for starting and stopping a QTimer that
will monitor "queued" signals and invoke their callbacks.  This is useful when
psygnal is used in a Qt application, and you'd like to emit signals from a thread
but have their callbacks invoked in the main thread.
"""

from __future__ import annotations

from threading import Thread, current_thread

from ._queue import emit_queued

try:
    from qtpy.QtCore import Qt, QTimer
except (ImportError, RuntimeError):  # pragma: no cover
    raise ImportError(
        "The psygnal.qt module requires qtpy and some Qt backend to be installed"
    ) from None

_TIMERS: dict[Thread, QTimer] = {}


def start_emitting_from_queue(
    msec: int = 0,
    timer_type: Qt.TimerType = Qt.TimerType.PreciseTimer,
    thread: Thread | None = None,
) -> None:
    """Start a QTimer that will monitor the global emission queue.

    If a QTimer is already running in the current thread, then this function will
    update the interval and timer type of that QTimer. (It is safe to call this
    function multiple times in the same thread.)

    When callbacks are connected to signals with `connect(type='queued')`, then they
    are not invoked immediately, but rather added to a global queue.  This function
    starts a QTimer that will periodically check the queue and invoke any callbacks
    that are waiting to be invoked (in whatever thread this QTimer is running in).

    Parameters
    ----------
    msec : int, optional
        The interval (in milliseconds) at which the QTimer will check the global
        emission queue.  By default, the QTimer will check the queue as often as
        possible (i.e. 0 milliseconds).
    timer_type : Qt.TimerType, optional
        The type of timer to use.  By default, Qt.PreciseTimer is used, which is
        the most accurate timer available on the system.
    thread : Thread, optional
        The thread in which to start the QTimer.  By default, the QTimer will be
        started in the thread from which this function is called.
    """
    _thread = current_thread() if thread is None else thread
    if _thread not in _TIMERS:
        _TIMERS[_thread] = QTimer()

        _TIMERS[_thread].timeout.connect(emit_queued)

    _TIMERS[_thread].setTimerType(timer_type)
    if _TIMERS[_thread].isActive():
        _TIMERS[_thread].setInterval(msec)
    else:
        _TIMERS[_thread].start(msec)


def stop_emitting_from_queue(thread: Thread | None = None) -> None:
    """Stop the QTimer that monitors the global emission queue.

    thread : Thread, optional
        The thread in which to stop the QTimer. By default, will stop any QTimers
        in the thread from which this function is called.
    """
    _thread = current_thread() if thread is None else thread
    if (timer := _TIMERS.get(_thread)) is not None:
        timer.stop()
