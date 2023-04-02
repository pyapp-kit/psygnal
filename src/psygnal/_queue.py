from queue import Queue
from typing import Any, Callable, Tuple

from ._weak_callback import WeakCallback

Callback = Callable[[tuple[Any, ...]], Any]
CbArgsTuple = Tuple[Callback, tuple]


class QueuedCallback(WeakCallback):
    _GLOBAL_QUEUE: Queue[CbArgsTuple] = Queue()

    def __init__(self, wrapped: WeakCallback) -> None:
        self._wrapped = wrapped
        self._key: str = wrapped._key
        self._max_args: int | None = wrapped._max_args
        self._alive: bool = wrapped._alive
        self._on_ref_error = wrapped._on_ref_error

    def cb(self, args: tuple = ()) -> None:
        self._GLOBAL_QUEUE.put((self._wrapped.cb, args))

    def dereference(self) -> Callable | None:
        return self._wrapped.dereference()


def emit_queued(queue: Queue[CbArgsTuple] = QueuedCallback._GLOBAL_QUEUE) -> None:
    from ._signal import EmitLoopError

    while not queue.empty():
        cb, args = queue.get()
        try:
            cb(args)
        except Exception as e:
            raise EmitLoopError(slot_repr=repr(cb), args=args, exc=e) from e
