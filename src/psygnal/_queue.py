from __future__ import annotations

from queue import Queue
from threading import Thread, current_thread, main_thread
from typing import Any, Callable, ClassVar, DefaultDict, Tuple

from ._exceptions import EmitLoopError
from ._weak_callback import WeakCallback

Callback = Callable[[Tuple[Any, ...]], Any]
CbArgsTuple = Tuple[Callback, tuple]


class QueuedCallback(WeakCallback):
    _GLOBAL_QUEUE: ClassVar[DefaultDict[Thread, Queue[CbArgsTuple]]] = DefaultDict(
        Queue
    )

    def __init__(self, wrapped: WeakCallback, thread: Thread | None = None) -> None:
        self._wrapped = wrapped
        self._key: str = wrapped._key
        self._max_args: int | None = wrapped._max_args
        self._alive: bool = wrapped._alive
        self._on_ref_error = wrapped._on_ref_error
        if thread is None:
            self._thread = main_thread()
        elif not isinstance(thread, Thread):
            raise TypeError(
                f"thread must be a Thread instance, not {type(thread).__name__}"
            )
        else:
            self._thread = thread

    def cb(self, args: tuple = ()) -> None:
        QueuedCallback._GLOBAL_QUEUE[self._thread].put((self._wrapped.cb, args))

    def dereference(self) -> Callable | None:
        return self._wrapped.dereference()


def emit_queued(queue: Queue[CbArgsTuple] | None = None) -> None:
    if queue is None:
        queue = QueuedCallback._GLOBAL_QUEUE[current_thread()]

    while not queue.empty():
        cb, args = queue.get()
        try:
            cb(args)
        except Exception as e:
            raise EmitLoopError(slot_repr=repr(cb), args=args, exc=e) from e
