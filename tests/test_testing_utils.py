import pytest

import psygnal.testing as pt
from psygnal import Signal


class MyObject:
    changed = Signal()
    value_changed = Signal(int)


def test_assert_emitted():
    obj = MyObject()

    with pt.assert_emitted(obj.changed):
        obj.changed.emit()

    with pytest.raises(
        AssertionError, match="Expected 'changed' to have been emitted."
    ):
        with pt.assert_emitted(obj.changed):
            pass

    with pt.assert_emitted_once(obj.changed):
        obj.changed.emit()

    with pytest.raises(AssertionError):
        with pt.assert_emitted_once(obj.changed):
            obj.changed.emit()
            obj.changed.emit()
