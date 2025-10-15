from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from queue import Queue
from threading import Thread, current_thread, main_thread
from typing import Any, ClassVar, Literal

from ._exceptions import EmitLoopError
from ._weak_callback import WeakCallback

Callback = Callable[[tuple[Any, ...]], Any]
CbArgsTuple = tuple[Callback, tuple]


class QueuedCallback(WeakCallback):
    """WeakCallback that queues the callback to be called on a different thread.

    (...rather than invoking it immediately.)

    Parameters
    ----------
    wrapped : WeakCallback
        The actual callback to be invoked.
    thread : Thread | Literal["main", "current"] | None
        The thread on which to invoke the callback.  If not provided, the main
        thread will be used.
    """

    _GLOBAL_QUEUE: ClassVar[defaultdict[Thread, Queue[CbArgsTuple]]] = defaultdict(
        Queue
    )

    def __init__(
        self,
        wrapped: WeakCallback,
        thread: Thread | Literal["main", "current"] | None = None,
    ) -> None:
        self._wrapped = wrapped
        # keeping the wrapped key allows this slot to be disconnected
        # regardless of whether it was connected with type='queue' or 'direct' ...
        self._key: str = wrapped._key
        self._max_args: int | None = wrapped._max_args
        self._alive: bool = wrapped._alive
        self._on_ref_error = wrapped._on_ref_error

        if thread is None or thread == "main":
            thread = main_thread()
        elif thread == "current":
            thread = current_thread()
        elif not isinstance(thread, Thread):  # pragma: no cover
            raise TypeError(
                f"`thread` must be a Thread instance, not {type(thread).__name__}"
            )
        # NOTE: for some strange reason, mypyc crashes if we use `self._thread` here
        # so we use `self._cbthread` instead
        self._cbthread = thread
        self.priority: int = wrapped.priority

    def cb(self, args: tuple = ()) -> None:
        if current_thread() is self._cbthread:
            self._wrapped.cb(args)
        else:
            QueuedCallback._GLOBAL_QUEUE[self._cbthread].put((self._wrapped.cb, args))

    def dereference(self) -> Callable | None:
        return self._wrapped.dereference()

    def __eq__(self, other: object) -> bool:
        """Compare QueuedCallback instances for equality based on wrapped callback.

        This method is explicitly defined to avoid mypyc gen_glue_ne_method
        AssertionError when building on Python 3.11+. Without this explicit
        definition, mypyc tries to generate glue methods for the inheritance
        hierarchy and fails with an AssertionError in gen_glue_ne_method.
        """
        if isinstance(other, QueuedCallback):
            return self._wrapped == other._wrapped
        return NotImplemented


def emit_queued(thread: Thread | None = None) -> None:
    """Trigger emissions of all callbacks queued in the current thread.

    Parameters
    ----------
    thread : Thread, optional
        The thread on which to invoke the callback.  If not provided, the main
        thread will be used.

    Raises
    ------
    EmitLoopError
        If an exception is raised while invoking a queued callback.
        This exception can be caught and optionally suppressed or handled by the caller,
        allowing the emission of other queued callbacks to continue even if one of them
        raises an exception.
    """
    _thread = current_thread() if thread is None else thread
    queue = QueuedCallback._GLOBAL_QUEUE[_thread]

    while not queue.empty():
        cb, args = queue.get()
        try:
            cb(args)
        except Exception as e:  # pragma: no cover
            raise EmitLoopError(exc=e) from e
