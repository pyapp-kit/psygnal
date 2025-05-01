import re

import pytest

import psygnal.testing as pt
from psygnal import Signal


class MyObject:
    changed = Signal()
    value_changed = Signal(int)


def test_assert_emitted() -> None:
    obj = MyObject()

    with pt.assert_emitted(obj.changed) as tester:
        obj.changed.emit()

    assert isinstance(tester, pt.SignalTester)

    with pytest.raises(
        AssertionError, match="Expected 'changed' to have been emitted."
    ):
        with pt.assert_emitted(obj.changed):
            pass


def test_assert_emitted_once():
    obj = MyObject()
    with pt.assert_emitted_once(obj.changed) as tester:
        obj.changed.emit()
    assert isinstance(tester, pt.SignalTester)

    with pytest.raises(
        AssertionError,
        match="Expected 'changed' to have been emitted once. Emitted 2 times.",
    ):
        with pt.assert_emitted_once(obj.changed):
            obj.changed.emit()
            obj.changed.emit()


def test_assert_not_emitted() -> None:
    obj = MyObject()
    with pt.assert_not_emitted(obj.changed) as tester:
        pass

    assert isinstance(tester, pt.SignalTester)

    with pytest.raises(
        AssertionError,
        match="Expected 'changed' to not have been emitted. Emitted once.",
    ):
        with pt.assert_not_emitted(obj.changed):
            obj.changed.emit()

    with pytest.raises(
        AssertionError,
        match="Expected 'changed' to not have been emitted. Emitted 4 times.",
    ):
        with pt.assert_not_emitted(obj.changed):
            obj.changed.emit()
            obj.changed.emit()
            obj.changed.emit()
            obj.changed.emit()


def test_assert_emitted_with() -> None:
    obj = MyObject()
    with pt.assert_emitted_with(obj.value_changed, 42) as tester:
        obj.value_changed.emit(41)
        obj.value_changed.emit(42)

    assert isinstance(tester, pt.SignalTester)

    with pytest.raises(
        AssertionError,
        match=re.escape(
            "Expected 'value_changed' to have been emitted with arguments (42,)."
            "\nActual: not emitted"
        ),
    ):
        with pt.assert_emitted_with(obj.value_changed, 42):
            pass

    with pytest.raises(
        AssertionError,
        match=re.escape(
            "Expected 'value_changed' to have been emitted with arguments (42,)."
            "\nActual: (43,)"
        ),
    ):
        with pt.assert_emitted_with(obj.value_changed, 42):
            obj.value_changed.emit(42)
            obj.value_changed.emit(43)


def test_assert_emitted_once_with() -> None:
    obj = MyObject()
    with pt.assert_emitted_once_with(obj.value_changed, 42) as tester:
        obj.value_changed.emit(42)

    assert isinstance(tester, pt.SignalTester)

    with pytest.raises(
        AssertionError,
        match=re.escape(
            "Expected 'value_changed' to have been emitted exactly once. "
            "Emitted 2 times."
        ),
    ):
        with pt.assert_emitted_once_with(obj.value_changed, 42):
            obj.value_changed.emit(42)
            obj.value_changed.emit(42)

    with pytest.raises(
        AssertionError,
        match=re.escape(
            "Expected 'value_changed' to have been emitted once with arguments (42,)."
            "\nActual: (43,)"
        ),
    ):
        with pt.assert_emitted_once_with(obj.value_changed, 42):
            obj.value_changed.emit(43)


def test_assert_ever_emitted_with() -> None:
    obj = MyObject()

    with pt.assert_ever_emitted_with(obj.value_changed, 42) as tester:
        obj.value_changed.emit(41)
        obj.value_changed.emit(42)
        obj.value_changed.emit(43)

    assert isinstance(tester, pt.SignalTester)

    with pytest.raises(
        AssertionError,
        match=re.escape(
            "Expected 'value_changed' to have been emitted at least once with "
            "arguments (42,)."
            "\nActual: not emitted"
        ),
    ):
        with pt.assert_ever_emitted_with(obj.value_changed, 42):
            pass

    with pytest.raises(
        AssertionError,
        match=re.escape(
            "Expected 'value_changed' to have been emitted at least once with "
            "arguments (42,)."
            "\nActual: (43,)"
        ),
    ):
        with pt.assert_ever_emitted_with(obj.value_changed, 42):
            obj.value_changed.emit(43)

    with pytest.raises(
        AssertionError,
        match=re.escape(
            "Expected 'value_changed' to have been emitted at least once with "
            "arguments (42,)."
            "\nActual: [(41,), (42, 43)]"
        ),
    ):
        with pt.assert_ever_emitted_with(obj.value_changed, 42):
            obj.value_changed.emit(41)
            obj.value_changed.emit(42, 43)


def test_signal_tester() -> None:
    obj = MyObject()
    tester = pt.SignalTester(obj.changed)
    tester.connect()
    assert tester.signal_name == "changed"
    assert tester.mock.call_count == 0

    obj.changed.emit()

    tester.assert_emitted_once()
    tester.assert_emitted()
    tester.assert_emitted_with()
    assert tester.emit_count == 1
    tester.reset()
    assert tester.emit_count == 0

    tester2 = pt.SignalTester(obj.value_changed)

    with tester2:
        obj.value_changed.emit(42)
        obj.value_changed.emit(43)

    tester2.assert_emitted()
    tester2.assert_emitted_with(43)
    tester2.assert_ever_emitted_with(42)

    assert tester2.emit_args_list == [(42,), (43,)]
    assert tester2.emit_count == 2
    assert tester2.emit_args == (43,)
