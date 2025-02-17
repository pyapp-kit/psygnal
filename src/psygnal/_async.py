from math import inf
from abc import ABC, abstractmethod


_async_backend = None


def get_async_backend():
    return _async_backend


def set_async_backend(backend: str = "asyncio"):
    global _async_backend

    if _async_backend is not None:
        raise RuntimeError(f"Async backend already set to: {_async_backend._backend}")

    if backend == "asyncio":

        import asyncio

        class AsyncBackend(_AsyncBackend):
            def __init__(self):
                super().__init__(backend)
                self._queue = asyncio.Queue()
                self._task = asyncio.create_task(self.run())

            def _put(self, item) -> None:
                self._queue.put_nowait(item)

            async def _get(self):
                return await self._queue.get()

            async def run(self) -> None:
                if self.__running:
                    return

                self.__running = True
                while True:
                    item = await self._get()
                    await self.call_back(item)

    elif backend == "anyio":

        import anyio

        class AsyncBackend(_AsyncBackend):
            def __init__(self):
                super().__init__(backend)
                self._send_stream, self._receive_stream = anyio.create_memory_object_stream(max_buffer_size=inf)

            def _put(self, item) -> None:
                self._send_stream.send_nowait(item)

            async def _get(self):
                return await self._receive_stream.receive()

            async def run(self) -> None:
                if self.__running:
                    return

                self.__running = True
                async with self._receive_stream:
                    async for item in self._receive_stream:
                        await self.call_back(item)

    elif backend == "trio":

        import trio

        class AsyncBackend(_AsyncBackend):
            def __init__(self):
                super().__init__(backend)
                self._send_channel, self._receive_channel = trio.open_memory_channel(max_buffer_size=inf)

            def _put(self, item) -> None:
                self._send_channel.send_nowait(item)

            async def _get(self):
                return await self._receive_channel.receive()

            async def run(self) -> None:
                if self.__running:
                    return

                self.__running = True
                async for item in self._receive_channel:
                    await self.call_back(item)

        _async_backend = AsyncBackend()

    else:
        raise RuntimeError(f"Async backend not supported: {backend}")

    _async_backend = AsyncBackend()
    return _async_backend


class _AsyncBackend(ABC):
    def __init__(self, backend: str):
        self._backend = backend
        self.__running = False

    @property
    def _running(self) -> bool:
        return self.__running

    @abstractmethod
    def _put(self, item) -> None:
        ...

    @abstractmethod
    async def _get(self):
        ...

    @abstractmethod
    async def run(self) -> None:
        ...

    async def call_back(self, item) -> None:
        cb = item[0]
        args = item[1:-1]
        kwargs = item[-1]
        await cb(*args, **kwargs)
