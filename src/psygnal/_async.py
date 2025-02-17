from __future__ import annotations

from abc import ABC, abstractmethod
from math import inf
from typing import TYPE_CHECKING, Any, Literal, TypeAlias, overload

if TYPE_CHECKING:
    from psygnal._weak_callback import WeakCallback

SupportedBackend = Literal["asyncio", "anyio", "trio"]
_async_backend: _AsyncBackend | None = None


def get_async_backend() -> _AsyncBackend | None:
    return _async_backend


@overload
def set_async_backend(backend: Literal["asyncio"]) -> AsyncioBackend: ...
@overload
def set_async_backend(backend: Literal["anyio"]) -> AnyioBackend: ...
@overload
def set_async_backend(backend: Literal["trio"]) -> TrioBackend: ...
def set_async_backend(backend: SupportedBackend = "asyncio") -> _AsyncBackend:
    global _async_backend

    if _async_backend is not None and _async_backend._backend != backend:
        raise RuntimeError(f"Async backend already set to: {_async_backend._backend}")

    if backend == "asyncio":
        _async_backend = AsyncioBackend()
    elif backend == "anyio":
        _async_backend = AnyioBackend()
    elif backend == "trio":
        _async_backend = TrioBackend()
    else:
        raise RuntimeError(
            f"Async backend not supported: {backend}.  "
            "Must be one of: 'asyncio', 'anyio', 'trio'"
        )

    return _async_backend


QueueItem: TypeAlias = tuple["WeakCallback", tuple[Any, ...]]


class _AsyncBackend(ABC):
    def __init__(self, backend: str):
        self._backend = backend
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    @abstractmethod
    def _put(self, item: QueueItem) -> None: ...

    @abstractmethod
    async def _get(self) -> QueueItem: ...

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

        self._queue: asyncio.Queue[tuple] = asyncio.Queue()
        self._task = asyncio.create_task(self.run())
        self._loop = asyncio.get_running_loop()

    def _put(self, item: QueueItem) -> None:
        self._queue.put_nowait(item)

    async def _get(self) -> QueueItem:
        return await self._queue.get()

    async def run(self) -> None:
        import asyncio

        if self.running:
            return

        self._running = True
        try:
            while True:
                item = await self._get()
                await self.call_back(item)
        except asyncio.CancelledError:
            pass
        except RuntimeError as e:
            if not self._loop.is_closed():
                raise e


class AnyioBackend(_AsyncBackend):
    if TYPE_CHECKING:
        import anyio.streams.memory

        _send_stream: anyio.streams.memory.MemoryObjectSendStream[QueueItem]
        _receive_stream: anyio.streams.memory.MemoryObjectReceiveStream[QueueItem]

    def __init__(self) -> None:
        super().__init__("anyio")
        import anyio

        self._send_stream, self._receive_stream = anyio.create_memory_object_stream(
            max_buffer_size=inf
        )

    def _put(self, item: QueueItem) -> None:
        self._send_stream.send_nowait(item)

    async def _get(self) -> QueueItem:
        return await self._receive_stream.receive()

    async def run(self) -> None:
        if self.running:
            return

        self._running = True
        async with self._receive_stream:
            async for item in self._receive_stream:
                await self.call_back(item)


class TrioBackend(_AsyncBackend):
    if TYPE_CHECKING:
        import trio

        _send_channel: trio._channel.MemorySendChannel[QueueItem]
        _receive_channel: trio.abc.ReceiveChannel[QueueItem]

    def __init__(self) -> None:
        super().__init__("trio")
        import trio

        self._send_channel, self._receive_channel = trio.open_memory_channel(
            max_buffer_size=inf
        )

    def _put(self, item: tuple) -> None:
        self._send_channel.send_nowait(item)

    async def _get(self) -> tuple:
        return await self._receive_channel.receive()

    async def run(self) -> None:
        if self.running:
            return

        self._running = True
        async for item in self._receive_channel:
            await self.call_back(item)
