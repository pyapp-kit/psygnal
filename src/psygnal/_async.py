from __future__ import annotations

from abc import ABC, abstractmethod
from math import inf
from typing import (
    TYPE_CHECKING,
    Any,
    Protocol,
    TypeAlias,
    TypeVar,
    overload,
    runtime_checkable,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from typing import Literal

    import anyio.streams.memory
    import trio

    from psygnal._weak_callback import WeakCallback

    SupportedBackend: TypeAlias = Literal["asyncio", "anyio", "trio"]
    QueueItem: TypeAlias = Callable[[], Awaitable[None]]


class EventLike(Protocol):
    """Flag that reports whether an async backend is running."""

    def is_set(self) -> bool:
        """Return `True` if the flag is set, `False` if not."""
        ...

    async def wait(self) -> object:
        """Wait until the flag is set."""
        ...


@runtime_checkable
class AsyncBackend(Protocol):
    """Interface an async backend must provide to run async callbacks.

    Each emission of a signal connected to a coroutine function calls `put`
    with an item: a callable that takes no arguments and returns an awaitable.
    `run` takes items off the queue and awaits `item()` for each one.
    """

    @property
    def running(self) -> EventLike:
        """Flag set while `run` is processing the queue."""
        ...

    def put(self, item: QueueItem) -> None:
        """Queue an item without blocking."""
        ...

    async def run(self) -> None:
        """Await queued items until cancelled."""
        ...


class _AsyncCall:
    """Queue item that awaits a weakly referenced coroutine callback, if alive."""

    __slots__ = ("_args", "_cb")

    def __init__(self, cb: WeakCallback[Any], args: tuple[Any, ...]) -> None:
        self._cb = cb
        self._args = args

    async def __call__(self) -> None:
        if func := self._cb.dereference():
            await func(*self._args)

    def __repr__(self) -> str:
        return f"<AsyncCall {self._cb.slot_repr()}{self._args}>"


_B = TypeVar("_B", bound=AsyncBackend)

_ASYNC_BACKEND: AsyncBackend | None = None


def get_async_backend() -> AsyncBackend | None:
    """Get the current async backend. Returns None if no backend is set."""
    return _ASYNC_BACKEND


def clear_async_backend() -> None:
    """Clear the current async backend, closing it if it is a built-in one."""
    global _ASYNC_BACKEND
    if isinstance(_ASYNC_BACKEND, _AsyncBackend):
        _ASYNC_BACKEND.close()
    _ASYNC_BACKEND = None


@overload
def set_async_backend(backend: Literal["asyncio"] = ...) -> AsyncioBackend: ...
@overload
def set_async_backend(backend: Literal["anyio"]) -> AnyioBackend: ...
@overload
def set_async_backend(backend: Literal["trio"]) -> TrioBackend: ...
@overload
def set_async_backend(backend: _B) -> _B: ...
def set_async_backend(
    backend: SupportedBackend | AsyncBackend = "asyncio",
) -> AsyncBackend:
    """Set the async backend to use.

    This should be done as early as possible, and *must* be called before calling
    `SignalInstance.connect` with a coroutine function.

    Parameters
    ----------
    backend
        One of `'asyncio'`, `'anyio'` or `'trio'` to create a built-in backend,
        or an object implementing [`AsyncBackend`][psygnal.AsyncBackend].

    Raises
    ------
    TypeError
        If `backend` is neither a string nor an `AsyncBackend`.
    RuntimeError
        If a different backend is already set, or the backend name is not supported.
    """
    global _ASYNC_BACKEND

    if not isinstance(backend, (str, AsyncBackend)):
        raise TypeError(
            f"Expected a backend name or an AsyncBackend, got {type(backend).__name__}"
        )

    if _ASYNC_BACKEND is not None and backend is not _ASYNC_BACKEND:
        current = getattr(_ASYNC_BACKEND, "_backend", _ASYNC_BACKEND)
        # allow setting the same built-in backend multiple times, for tests
        if current != backend:
            raise RuntimeError(f"Async backend already set to: {current!r}")

    if not isinstance(backend, str):
        _ASYNC_BACKEND = backend
    elif backend == "asyncio":
        _ASYNC_BACKEND = AsyncioBackend()
    elif backend == "anyio":
        _ASYNC_BACKEND = AnyioBackend()
    elif backend == "trio":
        _ASYNC_BACKEND = TrioBackend()
    else:  # pragma: no cover
        raise RuntimeError(
            f"Async backend not supported: {backend}.  "
            "Must be one of: 'asyncio', 'anyio', 'trio'"
        )

    return _ASYNC_BACKEND


class _AsyncBackend(ABC):
    def __init__(self, backend: str):
        self._backend = backend

    @property
    @abstractmethod
    def running(self) -> EventLike: ...

    @abstractmethod
    def put(self, item: QueueItem) -> None: ...

    @abstractmethod
    async def run(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...


class AsyncioBackend(_AsyncBackend):
    def __init__(self) -> None:
        super().__init__("asyncio")
        import asyncio

        self._asyncio = asyncio
        self._queue: asyncio.Queue[QueueItem] = asyncio.Queue()
        self._task = asyncio.create_task(self.run())
        self._loop = asyncio.get_running_loop()
        self._running = asyncio.Event()

    @property
    def running(self) -> EventLike:
        """Return the event indicating if the backend is running."""
        return self._running

    def put(self, item: QueueItem) -> None:
        self._queue.put_nowait(item)

    def close(self) -> None:
        """Close the asyncio backend and cancel tasks."""
        if hasattr(self, "_task") and not self._task.done():
            self._task.cancel()

    async def run(self) -> None:
        if self._running.is_set():
            return

        self._running.set()
        try:
            while True:
                item = await self._queue.get()
                try:
                    await item()
                except Exception:
                    # Log the exception but continue running
                    # This prevents one bad callback from crashing the backend
                    import traceback

                    traceback.print_exc()
        except self._asyncio.CancelledError:
            pass
        except RuntimeError as e:  # pragma: no cover
            if not self._loop.is_closed():
                raise e
        finally:
            self._running.clear()


class AnyioBackend(_AsyncBackend):
    _send_stream: anyio.streams.memory.MemoryObjectSendStream[QueueItem]
    _receive_stream: anyio.streams.memory.MemoryObjectReceiveStream[QueueItem]

    def __init__(self) -> None:
        super().__init__("anyio")
        import anyio

        self._anyio = anyio
        self._send_stream, self._receive_stream = anyio.create_memory_object_stream(
            max_buffer_size=inf
        )
        self._running = anyio.Event()

    @property
    def running(self) -> EventLike:
        """Return the event indicating if the backend is running."""
        return self._running

    def put(self, item: QueueItem) -> None:
        self._send_stream.send_nowait(item)

    def close(self) -> None:
        """Close the anyio streams."""
        if hasattr(self, "_send_stream"):
            self._send_stream.close()
        if hasattr(self, "_receive_stream"):
            self._receive_stream.close()

    async def run(self) -> None:
        if self._running.is_set():
            return  # pragma: no cover

        self._running.set()
        try:
            async with self._receive_stream:
                async for item in self._receive_stream:
                    try:
                        await item()
                    except Exception:
                        # Log the exception but continue running
                        import traceback

                        traceback.print_exc()
        finally:
            self._running = self._anyio.Event()
            # Ensure streams are closed
            self.close()


class TrioBackend(_AsyncBackend):
    _send_channel: trio._channel.MemorySendChannel[QueueItem]
    _receive_channel: trio.abc.ReceiveChannel[QueueItem]

    def __init__(self) -> None:
        super().__init__("trio")
        import trio

        self._trio = trio
        self._send_channel, self._receive_channel = trio.open_memory_channel(
            max_buffer_size=inf
        )
        self._running = self._trio.Event()

    @property
    def running(self) -> EventLike:
        """Return the event indicating if the backend is running."""
        return self._running

    def put(self, item: QueueItem) -> None:
        self._send_channel.send_nowait(item)

    def close(self) -> None:
        """Close the trio send channel."""
        self._send_channel.close()

    async def run(self) -> None:
        if self._running.is_set():
            return  # pragma: no cover

        self._running.set()
        try:
            async for item in self._receive_channel:
                try:
                    await item()
                except Exception:
                    # Log the exception but continue running
                    import traceback

                    traceback.print_exc()
        finally:
            self._running = self._trio.Event()
