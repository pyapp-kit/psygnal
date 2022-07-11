import threading
from typing import Callable, Optional

from ._signal import Signal


class Timer:
    timeout = Signal()

    def __init__(self, interval_msec: int = 1000):
        self._timer: Optional[_RepeatTimer] = None
        self._interval = interval_msec
        self._single = False

    def start(self, msec: Optional[int] = None) -> None:
        if msec is not None:
            self._interval = msec
        if self._timer is not None:
            self.stop()
        self._timer = _RepeatTimer(self._interval / 1000, self._timer_timeout)
        self._timer.start()

    def _timer_timeout(self) -> None:
        if self._single:
            self.stop()
        self.timeout.emit()

    def stop(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def __del__(self) -> None:
        if self._timer is not None:
            self.stop()

    @property
    def interval(self) -> float:
        return self._interval

    @interval.setter
    def interval(self, msec: int) -> None:
        self._interval = msec
        if self._timer is not None:
            self._timer.interval = msec / 1000

    @staticmethod
    def single_shot(msec: int, callback: Callable) -> None:
        assert msec > 0, "Timers cannot have negative timeouts"
        threading.Timer(msec / 1000, callback).start()

    singleShot = single_shot


class _RepeatTimer(threading.Timer):
    interval: float  # sec

    def run(self) -> None:
        while not self.finished.wait(self.interval):  # type: ignore
            self.function(*self.args, **self.kwargs)  # type: ignore
