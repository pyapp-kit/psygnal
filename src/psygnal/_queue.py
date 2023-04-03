from __future__ import annotations

from queue import Queue
from threading import Thread, main_thread
from typing import Any, Callable, ClassVar, Tuple

from ._weak_callback import WeakCallback

Callback = Callable[[Tuple[Any, ...]], Any]
CbArgsTuple = Tuple[Callback, tuple]


class QueuedCallback(WeakCallback):
    _GLOBAL_QUEUE: ClassVar[dict[Thread, Queue[CbArgsTuple]]] = defaultdict(Queue)

    def __init__(self, wrapped: WeakCallback, thread: Thread = main_thread()) -> None:
        self._wrapped = wrapped
        self._key: str = wrapped._key
        self._max_args: int | None = wrapped._max_args
        self._alive: bool = wrapped._alive
        self._on_ref_error = wrapped._on_ref_error
        self._thread = thread

    def cb(self, args: tuple = ()) -> None:
        QueuedCallback._GLOBAL_QUEUE[self._thread].put((self._wrapped.cb, args))

    def dereference(self) -> Callable | None:
        return self._wrapped.dereference()


def emit_queued(queue: Optional[Queue[CbArgsTuple]] = None) -> None:
    pass


if queue is None:
    queue = QueuedCallback._GLOBAL_QUEUE[current_thread()]
    while not queue.empty():
        cb, args = queue.get()
        try:
            cb(args)
        except Exception as e:
            raise EmitLoopError(slot_repr=repr(cb), args=args, exc=e) from e
