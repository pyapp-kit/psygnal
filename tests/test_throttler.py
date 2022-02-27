import time
from unittest.mock import Mock

from psygnal._throttler import debounced, throttled


def test_debounced() -> None:
    mock1 = Mock()
    f1 = debounced(mock1, timeout=5)
    f2 = Mock()

    [(f1(), f2()) for _ in range(10)]

    time.sleep(0.008)
    mock1.assert_called_once()

    assert f2.call_count == 10


def test_throttled() -> None:
    mock1 = Mock()
    f1 = throttled(mock1, timeout=5)
    f2 = Mock()

    [(f1(), f2()) for _ in range(10)]

    time.sleep(0.008)
    assert mock1.call_count == 2
    assert f2.call_count == 10
