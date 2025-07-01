from __future__ import annotations

import asyncio
import gc
import importlib.util
import signal
from typing import TYPE_CHECKING, Any, Callable, Literal, Protocol
from unittest.mock import Mock

import pytest
import pytest_asyncio

from psygnal import _async
from psygnal._weak_callback import WeakCallback, weak_callback

if TYPE_CHECKING:
    from collections.abc import Iterator

# Available backends for parametrization
AVAILABLE_BACKENDS = ["asyncio"]
if importlib.util.find_spec("trio") is not None:
    AVAILABLE_BACKENDS.append("trio")
if importlib.util.find_spec("anyio") is not None:
    AVAILABLE_BACKENDS.append("anyio")


class BackendTestRunner(Protocol):
    """Protocol for backend-specific test runners."""

    @property
    def backend_name(self) -> Literal["asyncio", "anyio", "trio"]:
        """Name of the backend being used."""
        ...

    async def sleep(self, duration: float) -> None:
        """Sleep for the given duration using backend-specific sleep."""
        ...

    def run_with_backend(self, test_func: Callable[[], Any]) -> Any:
        """Run a test function with proper backend setup and teardown. Synchronous."""
        ...


class AsyncioTestRunner:
    """Test runner for asyncio backend."""

    @property
    def backend_name(self) -> Literal["asyncio"]:
        return "asyncio"

    async def sleep(self, duration: float) -> None:
        await asyncio.sleep(duration)

    def run_with_backend(self, test_func: Callable[[], Any]) -> Any:
        """Run test with asyncio backend."""

        async def _run_test() -> Any:
            _async.clear_async_backend()
            backend = _async.set_async_backend("asyncio")

            # Wait for backend to be running
            await self._wait_for_backend_running(backend)

            try:
                return await test_func()
            finally:
                # Cleanup
                if hasattr(backend, "_task") and not backend._task.done():
                    backend._task.cancel()
                    try:
                        await backend._task
                    except asyncio.CancelledError:
                        pass
                _async.clear_async_backend()

        return asyncio.run(_run_test())

    async def _wait_for_backend_running(
        self, backend: _async._AsyncBackend, timeout: float = 1.0
    ) -> None:
        """Wait for backend to be running with a timeout."""
        start_time = asyncio.get_event_loop().time()
        while not backend.running.is_set():
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError("Backend did not start running within timeout")
            await asyncio.sleep(0)


class AnyioTestRunner:
    """Test runner for anyio backend."""

    @property
    def backend_name(self) -> Literal["anyio"]:
        return "anyio"

    async def sleep(self, duration: float) -> None:
        import anyio

        await anyio.sleep(duration)

    def run_with_backend(self, test_func: Callable[[], Any]) -> Any:
        """Run test with anyio backend using structured concurrency."""
        import anyio

        async def _run_test():
            _async.clear_async_backend()
            backend = _async.set_async_backend("anyio")

            result = None
            async with anyio.create_task_group() as tg:
                tg.start_soon(backend.run)

                # Wait for backend to be running
                await backend.running.wait()

                try:
                    result = await test_func()
                finally:
                    # Cancel task group to shutdown properly
                    tg.cancel_scope.cancel()

            _async.clear_async_backend()
            return result

        return anyio.run(_run_test)


class TrioTestRunner:
    """Test runner for trio backend."""

    @property
    def backend_name(self) -> Literal["trio"]:
        return "trio"

    async def sleep(self, duration: float) -> None:
        import trio

        await trio.sleep(duration)

    def run_with_backend(self, test_func: Callable[[], Any]) -> Any:
        """Run test with trio backend using structured concurrency."""

        # On Windows asyncio has probably left its FD installed
        try:
            signal.set_wakeup_fd(-1)  # restore default
        except (ValueError, AttributeError):
            pass  # not the main thread or not supported

        import trio

        result = None

        async def _trio_main():
            nonlocal result
            _async.clear_async_backend()
            backend = _async.set_async_backend("trio")

            # Use a timeout to prevent hanging
            with trio.move_on_after(5.0) as cancel_scope:
                async with trio.open_nursery() as nursery:
                    nursery.start_soon(backend.run)

                    # Wait for backend to be running
                    await backend.running.wait()

                    try:
                        result = await test_func()
                    finally:
                        # Cancel nursery to shutdown properly
                        nursery.cancel_scope.cancel()

            # Check if we timed out
            if cancel_scope.cancelled_caught:
                raise TimeoutError("Test timed out")

            _async.clear_async_backend()

        # Run in trio context
        trio.run(_trio_main)
        return result


async def mock_call_count(
    mock: Mock, runner: BackendTestRunner, max_iterations: int = 100
) -> None:
    """Wait for callback execution with backend-specific sleep."""
    for _ in range(max_iterations):
        await runner.sleep(0.01)
        if mock.call_count > 0:
            break


@pytest_asyncio.fixture
async def clean_async_backend():
    """Fixture to ensure clean async backend state."""
    _async.clear_async_backend()
    yield
    _async.clear_async_backend()


@pytest.fixture(params=AVAILABLE_BACKENDS)
def runner(
    request: pytest.FixtureRequest, clean_async_backend: None
) -> Iterator[BackendTestRunner]:
    """Get the backend runner for the specified backend."""
    mapping: dict[str, type[BackendTestRunner]] = {
        "asyncio": AsyncioTestRunner,
        "anyio": AnyioTestRunner,
        "trio": TrioTestRunner,
    }
    yield mapping[request.param]()


# Parametrized tests for all backends
@pytest.mark.parametrize(
    "slot_type",
    [
        "coroutinefunc",
        "weak_coroutinefunc",
        "coroutinemethod",
    ],
)
def test_slot_types_all_backends(runner: BackendTestRunner, slot_type: str) -> None:
    """Test async slot types with all available backends."""

    async def _test_slot_type():
        mock = Mock()
        final_mock = Mock()

        if slot_type in {"coroutinefunc", "weak_coroutinefunc"}:

            async def test_obj(x: int) -> int:
                mock(x)
                return x

            cb = weak_callback(
                test_obj,
                strong_func=(slot_type == "coroutinefunc"),
                finalize=final_mock,
            )
        elif slot_type == "coroutinemethod":

            class MyObj:
                async def coroutine_method(self, x: int) -> int:
                    mock(x)
                    return x

            obj = MyObj()
            cb = weak_callback(obj.coroutine_method, finalize=final_mock)

        assert isinstance(cb, WeakCallback)
        assert isinstance(cb.slot_repr(), str)
        assert cb.dereference() is not None

        # Test callback execution
        cb.cb((2,))
        await mock_call_count(mock, runner)
        mock.assert_called_once_with(2)

        # Test direct await
        mock.reset_mock()
        result = await cb(4)
        assert result == 4
        mock.assert_called_once_with(4)

        # Test weak reference cleanup
        if slot_type in {"coroutinefunc", "weak_coroutinefunc"}:
            del test_obj
        else:
            del obj
        gc.collect()

        if slot_type == "coroutinefunc":  # strong_func
            cb.cb((4,))
            await mock_call_count(mock, runner)
            mock.assert_called_with(4)
        else:
            await mock_call_count(final_mock, runner)
            final_mock.assert_called_once_with(cb)
            assert cb.dereference() is None
            with pytest.raises(ReferenceError):
                cb.cb((2,))
            with pytest.raises(ReferenceError):
                await cb(2)

    # Run the test with the appropriate backend
    runner.run_with_backend(_test_slot_type)


def test_backend_error_conditions(runner: BackendTestRunner) -> None:
    """Test backend error conditions and exception handling."""

    async def _test_errors():
        mock = Mock()

        async def test_coro(x: int) -> int:
            if x == 999:
                raise ValueError("Test error")
            mock(x)
            return x

        cb = weak_callback(test_coro, strong_func=True)

        # Test normal execution
        cb.cb((5,))
        await mock_call_count(mock, runner)
        mock.assert_called_once_with(5)

        # Test error case - should not crash the backend
        cb.cb((999,))
        await runner.sleep(0.1)  # Give time for error to be handled

        # Backend should still work after error
        mock.reset_mock()
        cb.cb((10,))
        await mock_call_count(mock, runner)
        mock.assert_called_once_with(10)

    # Run the test with the backend runner
    runner.run_with_backend(_test_errors)


@pytest.mark.usefixtures("clean_async_backend")
@pytest.mark.asyncio
async def test_run_method_early_return() -> None:
    """Test that run() method returns early if backend is already running."""
    backend = _async.set_async_backend("asyncio")

    # Wait for backend to be running
    start_time = asyncio.get_event_loop().time()
    while not backend.running.is_set():
        if asyncio.get_event_loop().time() - start_time > 1.0:
            raise TimeoutError("Backend did not start running within timeout")
        await asyncio.sleep(0)

    # Now calling run() again should return early
    await backend.run()

    # Backend should still be running
    assert backend.running.is_set()


@pytest.mark.parametrize("backend_name", AVAILABLE_BACKENDS)
def test_high_level_api(backend_name: Literal["trio", "asyncio", "anyio"]) -> None:
    """Test the exact usage pattern shown in the feature summary documentation."""

    def run_example() -> None:
        """The example from the feature summary, adapted for testing."""

        async def example_main() -> None:
            # Step 1: Set Backend Early (Once Per Application)
            backend = _async.set_async_backend(backend_name)

            # Step 2: Launch Backend in Your Event Loop (backend-specific)
            if backend_name == "asyncio":
                import asyncio

                # Start the backend as a background task
                async_backend = _async.get_async_backend()
                assert async_backend is not None
                task = asyncio.create_task(async_backend.run())

                # Wait for backend to be running
                await backend.running.wait()

            elif backend_name == "anyio":
                import anyio

                async with anyio.create_task_group() as tg:
                    # Start the backend in the task group
                    async_backend = _async.get_async_backend()
                    assert async_backend is not None
                    tg.start_soon(async_backend.run)

                    # Wait for backend to be running
                    await backend.running.wait()

                    # Run the actual example
                    await run_signal_example()

                    # Cancel to exit cleanly
                    tg.cancel_scope.cancel()
                return

            elif backend_name == "trio":
                import trio

                async with trio.open_nursery() as nursery:
                    # Start the backend in the nursery
                    async_backend = _async.get_async_backend()
                    assert async_backend is not None
                    nursery.start_soon(async_backend.run)

                    # Wait for backend to be running
                    await backend.running.wait()

                    # Run the actual example
                    await run_signal_example()

                    # Cancel to exit cleanly
                    nursery.cancel_scope.cancel()
                return

            # For asyncio, run the example after backend is started
            try:
                await run_signal_example()
            finally:
                if backend_name == "asyncio":
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

        async def run_signal_example() -> None:
            """Step 3: Connect Async Callbacks - the exact example from docs."""
            from psygnal import Signal

            class MyObj:
                value_changed = Signal(str)

                def set_value(self, value: str) -> None:
                    self.value_changed.emit(value)

            # Track calls for testing
            mock = Mock()

            async def on_value_changed(new_value: str) -> None:
                mock(new_value)

            obj = MyObj()
            obj.value_changed.connect(on_value_changed)
            obj.set_value("hello!")

            # Wait for callback to execute
            max_wait = 100
            for _ in range(max_wait):
                if mock.call_count > 0:
                    break
                if backend_name == "asyncio":
                    await asyncio.sleep(0.01)
                elif backend_name == "anyio":
                    import anyio

                    await anyio.sleep(0.01)
                elif backend_name == "trio":
                    import trio

                    await trio.sleep(0.01)

            # Verify the callback was called with the expected value
            assert mock.call_count == 1
            assert mock.call_args[0][0] == "hello!"

        # Run the example with the appropriate backend
        if backend_name == "asyncio":
            return asyncio.run(example_main())
        elif backend_name == "anyio":
            import anyio

            return anyio.run(example_main)
        elif backend_name == "trio":
            import trio

            return trio.run(example_main)

    # Clear any existing backend before test
    _async.clear_async_backend()
    try:
        run_example()
    finally:
        # Clean up after test
        _async.clear_async_backend()
