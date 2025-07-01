# Usage with `async/await`

Psygnal can be made to work with asynchronous functions (those defined with
`async def`) by setting an async backend.  The pattern is slightly different
depending on the async framework you are using, but the general idea is the same.

We currently support:

- [x] [`asyncio`](https://docs.python.org/3/library/asyncio.html)
- [x] [`anyio`](https://anyio.readthedocs.io/)
- [x] [`trio`](https://trio.readthedocs.io/)

## Premise

Assume you have a class that emits signals, and an async function that you want
to use as a callback:

```python
from psygnal import Signal


class MyObj:
    value_changed = Signal(str)

    def set_value(self, value: str) -> None:
        self.value_changed.emit(value)


async def on_value_changed(new_value: str) -> None:
    """Callback function that will be called when the value changes."""
    print(f"The new value is {new_value!r}")
```

## Connecting Async Callbacks

To connect the `value_changed` signal to the `on_value_changed` async function,
we need to:

1. Set up the async backend using [`set_async_backend()`][psygnal.set_async_backend],
   *inside* an async context.
2. Wait for the backend to be ready.
3. Connect the async function to the signal.

Then whenever `set_value()` is called, the `on_value_changed` async function will be
called asynchronously.

!!! tip "Order matters!"

    Failure to call `set_async_backend()` before connecting an async callback
    will result in `RuntimeError`.

    Failure to wait for the backend to be ready before connecting an async
    callback will result in a `RuntimeWarning`, and the callback will not
    be called.

=== "asyncio"

    ```python
    import asyncio

    from psygnal import set_async_backend


    async def main() -> None:
        backend = set_async_backend("asyncio") # (1)!

        # Set up the async backend and wait for it to be ready
        while not backend.running:  # (2)!
            await asyncio.sleep(0.01)

        # Create an instance of MyObj and connect the async callback
        obj = MyObj()
        obj.value_changed.connect(on_value_changed)  # (3)!

        # Set a value to trigger the callback
        obj.set_value("hello!")

        # Give the callback time to execute
        await asyncio.sleep(0.01)


    if __name__ == "__main__":
        asyncio.run(main())
    ```

    1.  Call `psygnal.set_async_backend("asyncio")`.  This immediately creates
        a task to process the queues.
    2.  Wait for the backend to task be ready before connecting the signal.
    3.  Connect the signal to the async callback function.

=== "AnyIO"

    ```python
    import anyio

    from psygnal import set_async_backend


    async def main() -> None:
        backend = set_async_backend("anyio") # (1)!

        async with anyio.create_task_group() as tg:
            # Set up the async backend and wait for it to be ready before connecting
            tg.start_soon(backend.run)  # (2)!
            await backend.running.wait()  # (3)!

            # Create an instance of MyObj and connect the async callback
            obj = MyObj()
            obj.value_changed.connect(on_value_changed)  # (4)!

            # Set a value to trigger the callback
            obj.set_value("hello!")

            # Give the callback time to execute
            await anyio.sleep(0.01)

            tg.cancel_scope.cancel()


    if __name__ == "__main__":
        anyio.run(main)
    ```

    1.  Call `psygnal.set_async_backend("anyio")` to create send/receive queues.
    2.  Start watching the queues in the background using `backend.run()`.
    3.  Wait for the backend to be ready before connecting the signal.
    4.  Connect the signal to the async callback function.

=== "trio"

    ```python
    import trio

    from psygnal import set_async_backend


    async def main() -> None:
        backend = set_async_backend("trio")  # (1)!

        async with trio.open_nursery() as nursery:
            # Set up the async backend and wait for it to be ready before connecting
            nursery.start_soon(backend.run)  # (2)!
            while not backend.running:  # (3)!
                await trio.sleep(0.01)

            # Create an instance of MyObj and connect the async callback
            obj = MyObj()
            obj.value_changed.connect(on_value_changed)  # (4)!

            # Set a value to trigger the callback
            obj.set_value("hello!")

            # Give the callback time to execute
            await trio.sleep(0.01)

            nursery.cancel_scope.cancel()


    if __name__ == "__main__":
        trio.run(main)
    ```

    1.  Call `psygnal.set_async_backend("trio")` to create send/receive channels.
    2.  Start watching the channels in the background using `backend.run()`.
    3.  Wait for the backend to be ready before connecting the signal.
    4.  Connect the signal to the async callback function.
