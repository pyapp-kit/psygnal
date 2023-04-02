from __future__ import annotations

from queue import Queue
from typing import TYPE_CHECKING, Tuple, TypeVar

from typing_extensions import Protocol

if TYPE_CHECKING:
    from psygnal import SignalInstance

T = TypeVar("T")


class QueueLike(Protocol[T]):
    """A protocol for a queue-like object.

    This is used to type the `queue` argument to `emit_queued()`.
    """

    def empty(self) -> bool:
        ...

    def get(self, block: bool = True, timeout: float | None = None) -> T:
        ...

    def put(self, item: T, block: bool = True, timeout: float | None = None) -> None:
        ...


SigArgTuple = Tuple[SignalInstance, tuple]
SignalQueue = Queue[SigArgTuple]
_GLOBAL_QUEUE: Queue[SigArgTuple] = Queue()


def emit_queued(queue: SignalQueue = _GLOBAL_QUEUE) -> None:
    """Emit all signals that have been queued with `self.queue_emit()`.

    This method is thread safe.

    This is designed to be called from the main thread in some sort of event
    loop, and will emit all signals that have been queued with `self.queue_emit()`
    (which may have been queued from a different thread).

    How you call this method is up to you.  For example, in Qt, you could call it
    from a QTimer, or from a QEventLoop:

    Examples
    --------
    ```python
    from qtpy.QtCore import QTimer, Qt
    from psygnal import Signal, emit_queued
    import threading

    class Emitter:
        sig = Signal(int)

    obj = Emitter()

    @obj.sig.connect
    def on_emit(value: int):
        print(f"got value {value} from thread {threading.current_thread().name!r}")

    # this timer lives in the main thread
    timer = QTimer()

    # whenever the timer times out, it will call `emit_queued`
    timer.timeout.connect(emit_queued)
    timer.start(0)  # start the timer

    def _some_thread_that_emits() -> None:
        # inside the thread call `emit()` with `queue=True`
        obj.sig.emit(1, queue=True)

    threading.Thread(target=_some_thread_that_emits).start()
    ```
    """
    while not queue.empty():
        sig, args = queue.get()
        sig._run_emit_loop(args)
