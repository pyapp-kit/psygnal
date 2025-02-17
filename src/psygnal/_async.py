_async_backend = None


def get_async_backend():
    return _async_backend


def set_async_backend(backend: str = "asyncio"):
    global _async_backend

    if _async_backend is not None:
        raise RuntimeError(f"Async backend already set to: {_async_backend._backend}")

    if backend == "asyncio":

        import asyncio

        class AsyncBackend:
            def __init__(self):
                self._backend = backend
                self._queue = asyncio.Queue()
                self.__running = False
                self._task = asyncio.create_task(self.run())

            @property
            def _running(self) -> bool:
                return self.__running

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
                    cb = item[0]
                    args = item[1:-1]
                    kwargs = item[-1]
                    await cb(*args, **kwargs)

        _async_backend = AsyncBackend()

    elif backend == "anyio":

        import anyio

        class AsyncBackend:
            def __init__(self):
                self._backend = backend
                self._send_stream, self._receive_stream = anyio.create_memory_object_stream(max_buffer_size=float("inf"))
                self.__running = False

            @property
            def _running(self) -> bool:
                return self.__running

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
                        cb = item[0]
                        args = item[1:-1]
                        kwargs = item[-1]
                        await cb(*args, **kwargs)

        _async_backend = AsyncBackend()

    else:
        raise RuntimeError(f"Async backend not supported: {backend}")

    return _async_backend
