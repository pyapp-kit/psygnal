"""Utilities for testing psygnal Signals."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING
from unittest.mock import Mock
from unittest.util import safe_repr

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any

    from typing_extensions import Self

    import psygnal

__all__ = [
    "SignalTester",
    "assert_emitted",
    "assert_emitted_once",
    "assert_emitted_once_with",
    "assert_emitted_with",
    "assert_ever_emitted_with",
    "assert_not_emitted",
]


class SignalTester:
    """A tester object that listens to a signal and records its emissions.

    This class wraps a [`psygnal.SignalInstance`][] and a [`unittest.mock.Mock`][]
    object. It provides methods to connect and disconnect the mock from the signal, and
    to assert that the signal was emitted with the expected arguments.  It also behaves
    as a **context manager**, so you can monitor emissions of a signal within a specific
    context.

    !!! important

        The signal is *not* automatically connected to the mock when the SignalTester is
        created. You must call [`connect()`][psygnal.testing.SignalTester.connect] or
        use the context manager to connect the mock to the signal.

    Parameters
    ----------
    signal_instance : psygnal.SignalInstance
        The signal instance to test.

    Attributes
    ----------
    signal_instance : psygnal.SignalInstance
        The signal instance to test.
    mock : unittest.mock.Mock
        The mock object that will be connected to the signal.

    Examples
    --------
    ```python
    from psygnal import Signal
    from psygnal.testing import SignalTester


    class MyObject:
        value_changed = Signal(int)


    obj = MyObject()
    tester = SignalTester(obj.value_changed)
    tester.assert_not_emitted()

    with tester:
        obj.value_changed.emit(1)

    tester.assert_emitted()
    tester.assert_emitted_once()
    tester.assert_emitted_once_with(1)
    assert tester.emit_count == 1
    tester.reset()
    assert tester.emit_count == 0
    ```
    """

    def __init__(self, signal_instance: psygnal.SignalInstance) -> None:
        super().__init__()
        self.mock = Mock()
        self.signal_instance = signal_instance

    def reset(self) -> None:
        """Reset the underlying mock object."""
        self.mock.reset_mock()

    @property
    def emit_count(self) -> int:
        """Return the number of times the signal was emitted."""
        return self.mock.call_count

    @property
    def emit_args(self) -> tuple[Any, ...]:
        """Return the arguments of the last emission of the signal."""
        if (call_args := self.mock.call_args) is None:
            return ()

        return call_args[0]  # type: ignore[no-any-return]

    @property
    def emit_args_list(self) -> list[tuple[Any, ...]]:
        """Return the arguments of all emissions of the signal."""
        return [call[0] for call in self.mock.call_args_list]

    def connect(self) -> None:
        """Connect the mock to the signal."""
        self.signal_instance.connect(self.mock)

    def disconnect(self) -> None:
        """Disconnect the mock from the signal."""
        self.signal_instance.disconnect(self.mock)

    def __enter__(self) -> Self:
        """Connect the mock to the signal."""
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        """Disconnect the mock from the signal."""
        self.disconnect()

    @property
    def signal_name(self) -> str:
        """Return the name of the signal."""
        return self.signal_instance.name or "signal"

    def assert_not_emitted(self) -> None:
        """Assert that the signal was never emitted."""
        if self.mock.call_count != 0:
            if self.mock.call_count == 1:
                n = "once"
            else:
                n = f"{self.mock.call_count} times"
            raise AssertionError(
                f"Expected {self.signal_name!r} to not have been emitted. Emitted {n}."
            )

    def assert_emitted(self) -> None:
        """Assert that the signal was emitted at least once."""
        if self.mock.call_count == 0:
            raise AssertionError(f"Expected {self.signal_name!r} to have been emitted.")

    def assert_emitted_once(self) -> None:
        """Assert that the signal was emitted exactly once."""
        if not self.mock.call_count == 1:
            raise AssertionError(
                f"Expected {self.signal_name!r} to have been emitted once. "
                f"Emitted {self.mock.call_count} times."
            )

    def assert_emitted_with(self, /, *args: Any) -> None:
        """Assert that the *last* emission of the signal had the given arguments."""
        if self.mock.call_args is None:
            raise AssertionError(
                f"Expected {self.signal_name!r} to have been emitted with arguments "
                f"{args!r}.\nActual: not emitted"
            )

        actual = self.mock.call_args[0]
        if actual != args:
            raise AssertionError(
                f"Expected {self.signal_name!r} to have been emitted with arguments "
                f"{args!r}.\nActual: {actual}"
            )

    def assert_emitted_once_with(self, /, *args: Any) -> None:
        """Assert that the signal was emitted exactly once with the given arguments."""
        if not self.mock.call_count == 1:
            raise AssertionError(
                f"Expected {self.signal_name!r} to have been emitted exactly once. "
                f"Emitted {self.mock.call_count} times."
            )

        actual = self.mock.call_args[0]
        if actual != args:
            raise AssertionError(
                f"Expected {self.signal_name!r} to have been emitted once with "
                f"arguments {args!r}.\nActual: {safe_repr(actual)}"
            )

    def assert_ever_emitted_with(self, /, *args: Any) -> None:
        """Assert that the signal was emitted *ever* with the given arguments."""
        if self.mock.call_args is None:
            raise AssertionError(
                f"Expected {self.signal_name!r} to have been emitted at least once "
                f"with arguments {args!r}.\nActual: not emitted"
            )

        actual = [call[0] for call in self.mock.call_args_list]
        if not any(call == args for call in actual):
            _actual: tuple | list = actual[0] if len(actual) == 1 else actual
            raise AssertionError(
                f"Expected {self.signal_name!r} to have been emitted at least once "
                f"with arguments {args!r}.\nActual: {safe_repr(_actual)}"
            )


@contextmanager
def assert_emitted(signal: psygnal.SignalInstance) -> Iterator[SignalTester]:
    """Assert that a signal was emitted at least once.

    Parameters
    ----------
    signal : psygnal.SignalInstance
        The signal instance to test.

    Raises
    ------
    AssertionError
        If the signal was never emitted.
    """
    with SignalTester(signal) as mock:
        yield mock
        mock.assert_emitted()


@contextmanager
def assert_emitted_once(signal: psygnal.SignalInstance) -> Iterator[SignalTester]:
    """Assert that a signal was emitted exactly once.

    Parameters
    ----------
    signal : psygnal.SignalInstance
        The signal instance to test.

    Raises
    ------
    AssertionError
        If the signal was emitted more than once.
    """
    with SignalTester(signal) as mock:
        yield mock
        mock.assert_emitted_once()


@contextmanager
def assert_not_emitted(signal: psygnal.SignalInstance) -> Iterator[SignalTester]:
    """Assert that a signal was never emitted.

    Parameters
    ----------
    signal : psygnal.SignalInstance
        The signal instance to test.

    Raises
    ------
    AssertionError
        If the signal was emitted at least once.
    """
    with SignalTester(signal) as mock:
        yield mock
        mock.assert_not_emitted()


@contextmanager
def assert_emitted_with(
    signal: psygnal.SignalInstance, *args: Any
) -> Iterator[SignalTester]:
    """Assert that the *last* emission of the signal had the given arguments.

    Parameters
    ----------
    signal : psygnal.SignalInstance
        The signal instance to test.
    args : Any
        The arguments to check for in the last emission of the signal.

    Raises
    ------
    AssertionError
        If the signal was never emitted or if the last emission did not have the
        expected arguments.
    """
    with assert_emitted(signal) as mock:
        yield mock
        mock.assert_emitted_with(*args)


@contextmanager
def assert_emitted_once_with(
    signal: psygnal.SignalInstance, *args: Any
) -> Iterator[SignalTester]:
    """Assert that the signal was emitted exactly once with the given arguments.

    Parameters
    ----------
    signal : psygnal.SignalInstance
        The signal instance to test.
    args : Any
        The arguments to check for in the last emission of the signal.

    Raises
    ------
    AssertionError
        If the signal was not emitted or was emitted more than once or if the last
        emission did not have the expected arguments.
    """
    with assert_emitted_once(signal) as mock:
        yield mock
        mock.assert_emitted_once_with(*args)


@contextmanager
def assert_ever_emitted_with(
    signal: psygnal.SignalInstance, *args: Any
) -> Iterator[SignalTester]:
    """Assert that the signal was emitted *ever* with the given arguments.

    Parameters
    ----------
    signal : psygnal.SignalInstance
        The signal instance to test.
    args : Any
        The arguments to check for in any emission of the signal.

    Raises
    ------
    AssertionError
        If the signal was never emitted or if it was emitted but not with the expected
        arguments.
    """
    with assert_emitted(signal) as mock:
        yield mock
        mock.assert_ever_emitted_with(*args)
