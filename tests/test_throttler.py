import time
from inspect import Parameter, signature
from typing import Callable
from unittest.mock import Mock

import pytest

from psygnal import SignalInstance, _compiled, debounced, throttled


def test_debounced() -> None:
    mock1 = Mock()
    f1 = debounced(mock1, timeout=10, leading=False)
    f2 = Mock()

    for _ in range(10):
        f1()
        f2()

    time.sleep(0.1)
    mock1.assert_called_once()

    assert f2.call_count == 10


def test_debounced_leading() -> None:
    mock1 = Mock()
    f1 = debounced(mock1, timeout=10, leading=True)
    f2 = Mock()

    for _ in range(10):
        f1()
        f2()

    time.sleep(0.1)
    assert mock1.call_count == 2
    assert f2.call_count == 10


def test_throttled() -> None:
    mock1 = Mock()
    f1 = throttled(mock1, timeout=10, leading=True)
    f2 = Mock()

    for _ in range(10):
        f1()
        f2()

    time.sleep(0.1)
    assert mock1.call_count == 2
    assert f2.call_count == 10


def test_throttled_trailing() -> None:
    mock1 = Mock()
    f1 = throttled(mock1, timeout=10, leading=False)
    f2 = Mock()

    for _ in range(10):
        f1()
        f2()

    time.sleep(0.1)
    assert mock1.call_count == 1
    assert f2.call_count == 10


def test_cancel() -> None:
    mock1 = Mock()
    f1 = debounced(mock1, timeout=50, leading=False)
    f1()
    f1()
    f1.cancel()
    time.sleep(0.2)
    mock1.assert_not_called()


def test_flush() -> None:
    mock1 = Mock()
    f1 = debounced(mock1, timeout=50, leading=False)
    f1()
    f1()
    f1.flush()
    time.sleep(0.2)
    mock1.assert_called_once()


@pytest.mark.parametrize("deco", [debounced, throttled])
def test_throttled_debounced_signature(deco: Callable) -> None:
    mock = Mock()

    @deco(timeout=0, leading=True)
    def f1(x: int) -> None:
        """Doc."""
        mock(x)

    # make sure we can still inspect the signature
    assert signature(f1).parameters["x"] == Parameter(
        "x", Parameter.POSITIONAL_OR_KEYWORD, annotation=int
    )

    # make sure these are connectable
    sig = SignalInstance((int, int, int))
    sig.connect(f1)
    sig.emit(1, 2, 3)
    mock.assert_called_once_with(1)

    if not _compiled:
        # unfortunately, dynamic assignment of __doc__ and stuff isn't possible in mypyc
        assert f1.__doc__ == "Doc."
        assert f1.__name__ == "f1"
