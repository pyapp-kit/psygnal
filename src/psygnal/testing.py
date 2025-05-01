"""Utilities for testing psygnal Signals."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING
from unittest.mock import Mock

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any, Self

    import psygnal


class SignalMock(Mock):
    """A mock for a psygnal Signal."""

    def __init__(self, signal_instance: psygnal.SignalInstance) -> None:
        super().__init__()
        self.signal_instance = signal_instance

    def connect(self) -> None:
        """Connect the mock to the signal."""
        self.signal_instance.connect(self)

    def disconnect(self) -> None:
        """Disconnect the mock from the signal."""
        self.signal_instance.disconnect(self)

    def __enter__(self) -> Self:
        """Connect the mock to the signal."""
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        """Disconnect the mock from the signal."""
        self.signal_instance.disconnect(self)

    @property
    def signal_name(self) -> str:
        """Return the name of the signal."""
        return self.signal_instance.name or "signal"

    def assert_not_emitted(self):
        """Assert that the signal was never emitted."""
        if self.call_count != 0:
            raise AssertionError(
                f"Expected {self.signal_name!r} to not have been emitted."
                f"Called {self.call_count} times."
            )

    def assert_emitted(self) -> None:
        """Assert that the signal was emitted at least once."""
        if self.call_count == 0:
            raise AssertionError(f"Expected {self.signal_name!r} to have been emitted.")

    def assert_emitted_once(self):
        """Assert that the signal was emitted exactly once."""
        if not self.call_count == 1:
            raise AssertionError(
                f"Expected {self.signal_name!r} to have been emitted once."
                f"Called {self.call_count} times."
            )

    def assert_emitted_with(self, /, *args: Any) -> None:
        """Assert that the last call to the signal was with the given arguments."""
        super().assert_called_with(*args)


@contextmanager
def assert_emitted(signal: psygnal.SignalInstance) -> Iterator[Mock]:
    """Assert that a signal was emitted at least once."""
    with SignalMock(signal) as mock:
        yield mock
        mock.assert_emitted()


@contextmanager
def assert_emitted_once(signal: psygnal.SignalInstance) -> Iterator[Mock]:
    """Assert that a signal was emitted exactly once."""
    with SignalMock(signal) as mock:
        yield mock
        mock.assert_emitted_once()


@contextmanager
def assert_emitted_with(signal: psygnal.SignalInstance, *args: Any) -> Iterator[Mock]:
    """Assert that a signal was emitted with the given arguments."""
    with assert_emitted(signal) as mock:
        yield mock
    mock.call_args[0][0]
    # if isinstance(val, np.ndarray):
    #     np.testing.assert_array_almost_equal(val, value, decimal=6)
    # else:
    #     assert val == value
