from __future__ import annotations

from abc import ABC, abstractmethod
from math import inf
from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, Literal, Protocol, TypeAlias

    import anyio.streams.memory
    import trio

    from psygnal._weak_callback import WeakCallback

    SupportedBackend: TypeAlias = Literal["asyncio", "anyio", "trio"]
    QueueItem: TypeAlias = tuple["WeakCallback", tuple[Any, ...]]

    class EventLike(Protocol):
        def is_set(self) -> bool:
            """Return ``True`` if the flag is set, ``False`` if not."""
            ...

        async def wait(self) -> Coroutine | bool | None:
            """Wait until the flag is set."""
            ...


_ASYNC_BACKEND: _AsyncBackend | None = None


def get_async_backend() -> _AsyncBackend | None:
    """Get the current async backend. Returns None if no backend is set."""
    return _ASYNC_BACKEND


def clear_async_backend() -> None:
    """Clear the current async backend. Primarily for testing purposes."""
    global _ASYNC_BACKEND
    if _ASYNC_BACKEND is not None:
        # Cancel any running tasks if it's asyncio and loop is not closed
        if isinstance(_ASYNC_BACKEND, AsyncioBackend):
            _ASYNC_BACKEND.close()
        # Close anyio streams
        elif isinstance(_ASYNC_BACKEND, AnyioBackend):
            _ASYNC_BACKEND.close()
        # Close trio channels
        elif isinstance(_ASYNC_BACKEND, TrioBackend):
            if hasattr(_ASYNC_BACKEND, "_send_channel"):
                _ASYNC_BACKEND._send_channel.close()
            # Note: trio receive channels don't have a close method
    _ASYNC_BACKEND = None


@overload
def set_async_backend(backend: Literal["asyncio"]) -> AsyncioBackend: ...
@overload
def set_async_backend(backend: Literal["anyio"]) -> AnyioBackend: ...
@overload
def set_async_backend(backend: Literal["trio"]) -> TrioBackend: ...
def set_async_backend(backend: SupportedBackend = "asyncio") -> _AsyncBackend:
    """Set the async backend to use. Must be one of: 'asyncio', 'anyio', 'trio'.

    This should be done as early as possible, and *must* be called before calling
    `SignalInstance.connect` with a coroutine function.
    """
    global _ASYNC_BACKEND

    if _ASYNC_BACKEND and _ASYNC_BACKEND._backend != backend:  # pragma: no cover
        # allow setting the same backend multiple times, for tests
        raise RuntimeError(f"Async backend already set to: {_ASYNC_BACKEND._backend}")

    if backend == "asyncio":
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

    async def call_back(self, item: QueueItem) -> None:
        cb, args = item
        if func := cb.dereference():
            await func(*args)


class AsyncioBackend(_AsyncBackend):
    def __init__(self) -> None:
        super().__init__("asyncio")
        import asyncio

        self._asyncio = asyncio
        self._queue: asyncio.Queue[tuple] = asyncio.Queue()
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
                    await self.call_back(item)
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
                        await self.call_back(item)
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

    def put(self, item: tuple) -> None:
        self._send_channel.send_nowait(item)

    async def run(self) -> None:
        if self._running.is_set():
            return  # pragma: no cover

        self._running.set()
        try:
            async for item in self._receive_channel:
                try:
                    await self.call_back(item)
                except Exception:
                    # Log the exception but continue running
                    import traceback

                    traceback.print_exc()
        finally:
            self._running = self._trio.Event()
