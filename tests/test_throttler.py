import time
from unittest.mock import Mock

from psygnal import debounced, throttled


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
