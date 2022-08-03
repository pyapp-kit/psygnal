import os
from typing import List, cast
from unittest.mock import Mock, call

import numpy as np
import pytest

from psygnal import EmissionInfo, Signal, SignalGroup
from psygnal.containers import EventedList


@pytest.fixture
def regular_list():
    return list(range(5))


@pytest.fixture
def test_list(regular_list):
    test_list = EventedList(regular_list)
    test_list.events = Mock(wraps=test_list.events)
    return test_list


@pytest.mark.parametrize(
    "meth",
    [
        # METHOD, ARGS, EXPECTED EVENTS
        # primary interface
        ("insert", (2, 10), ("inserting", "inserted")),  # create
        ("__getitem__", (2,), ()),  # read
        ("__setitem__", (2, 3), ("changed",)),  # update
        ("__setitem__", (slice(2), [1, 2]), ("changed",)),  # update slice
        ("__setitem__", (slice(2, 2), [1, 2]), ("changed",)),  # update slice
        ("__delitem__", (2,), ("removing", "removed")),  # delete
        (
            "__delitem__",
            (slice(2),),
            ("removing", "removed") * 2,
        ),
        ("__delitem__", (slice(0, 0),), ("removing", "removed")),
        (
            "__delitem__",
            (slice(-3),),
            ("removing", "removed") * 2,
        ),
        (
            "__delitem__",
            (slice(-2, None),),
            ("removing", "removed") * 2,
        ),
        # inherited interface
        ("append", (3,), ("inserting", "inserted")),
        ("clear", (), ("removing", "removed") * 5),
        ("count", (3,), ()),
        ("extend", ([7, 8, 9],), ("inserting", "inserted") * 3),
        ("index", (3,), ()),
        ("pop", (-2,), ("removing", "removed")),
        ("remove", (3,), ("removing", "removed")),
        ("reverse", (), ("reordered",)),
        ("__add__", ([7, 8, 9],), ()),
        ("__iadd__", ([7, 9],), ("inserting", "inserted") * 2),
        ("__radd__", ([7, 9],), ("inserting", "inserted") * 2),
        # sort?
    ],
    ids=lambda x: x[0],
)
def test_list_interface_parity(test_list, regular_list, meth):
    test_list.events = cast("Mock", test_list.events)

    method_name, args, expected = meth
    test_list_method = getattr(test_list, method_name)
    assert tuple(test_list) == tuple(regular_list)
    if hasattr(regular_list, method_name):
        regular_list_method = getattr(regular_list, method_name)
        assert test_list_method(*args) == regular_list_method(*args)
        assert tuple(test_list) == tuple(regular_list)
    else:
        test_list_method(*args)  # smoke test

    for c, expect in zip(test_list.events.call_args_list, expected):
        event = c.args[0]
        assert event.type == expect


def test_delete(test_list):
    assert test_list == [0, 1, 2, 3, 4]

    del test_list[1]
    assert test_list == [0, 2, 3, 4]

    del test_list[2:]
    assert test_list == [0, 2]


@pytest.mark.xfail("i686" in os.getenv("AUDITWHEEL_PLAT", ""), reason="failing on i686")
def test_hash(test_list):
    assert id(test_list) == hash(test_list)

    b = EventedList([2, 3], hashable=False)
    with pytest.raises(TypeError):
        hash(b)


def test_repr(test_list):
    assert repr(test_list) == "EventedList([0, 1, 2, 3, 4])"


def test_reverse(test_list):
    assert test_list == [0, 1, 2, 3, 4]
    test_list.reverse()
    test_list.events.reordered.emit.assert_called_once()
    test_list.events.changed.emit.assert_not_called()
    assert test_list == [4, 3, 2, 1, 0]

    test_list.events.reordered.emit.reset_mock()
    test_list.reverse(emit_individual_events=True)
    test_list.events.reordered.emit.assert_called_once()
    assert test_list.events.changed.emit.call_count == 4
    test_list.events.changed.emit.assert_has_calls(
        [call(0, 4, 0), call(4, 0, 4), call(1, 3, 1), call(3, 1, 3)]
    )
    assert test_list == [0, 1, 2, 3, 4]


def test_list_interface_exceptions(test_list):
    bad_index = {"a": "dict"}
    with pytest.raises(TypeError):
        test_list[bad_index]

    with pytest.raises(TypeError):
        test_list[bad_index] = 1

    with pytest.raises(TypeError):
        del test_list[bad_index]

    with pytest.raises(TypeError):
        test_list.insert([bad_index], 0)


def test_copy(test_list, regular_list):
    """Copying an evented list should return a same-class evented list."""
    new_test = test_list.copy()
    new_reg = regular_list.copy()
    assert id(new_test) != id(test_list)
    assert new_test == test_list
    assert tuple(new_test) == tuple(test_list) == tuple(new_reg)
    test_list.events.assert_not_called()


def test_array_like_setitem():
    """Test that EventedList.__setitem__ works for array-like items"""
    array = np.array((10, 10))
    evented_list = EventedList([array])
    evented_list[0] = array


def test_slice(test_list, regular_list):
    """Slicing an evented list should return a same-class evented list."""
    test_slice = test_list[1:3]
    regular_slice = regular_list[1:3]
    assert tuple(test_slice) == tuple(regular_slice)
    assert isinstance(test_slice, test_list.__class__)

    change_emit = test_list.events.changed.emit

    assert test_list == [0, 1, 2, 3, 4]
    test_list[1:3] = [6, 7, 8]
    assert test_list == [0, 6, 7, 8, 3, 4]
    change_emit.assert_called_with(slice(1, 3, None), [1, 2], [6, 7, 8])

    with pytest.raises(ValueError) as e:
        test_list[1:6:2] = [6, 7, 8, 6, 7]
    assert str(e.value).startswith("attempt to assign sequence of size 5 to extended ")

    test_list[1:6:2] = [9, 9, 9]
    assert test_list == [0, 9, 7, 9, 3, 9]
    change_emit.assert_called_with(slice(1, 6, 2), [6, 8, 4], [9, 9, 9])

    with pytest.raises(TypeError) as e2:
        test_list[1:3] = 1
    assert str(e2.value) == "Can only assign an iterable to slice"


def test_move(test_list: EventedList):
    """Test the that we can move objects with the move method"""
    test_list.events = cast("Mock", test_list.events)

    def _fail() -> None:
        raise AssertionError("unexpected event called")

    test_list.events.removing.connect(_fail)
    test_list.events.removed.connect(_fail)
    test_list.events.inserting.connect(_fail)
    test_list.events.inserted.connect(_fail)

    before = list(test_list)
    assert before == [0, 1, 2, 3, 4]  # from fixture
    # pop the object at 0 and insert at current position 3
    test_list.move(0, 3)
    expectation = [1, 2, 0, 3, 4]
    assert test_list != before
    assert test_list == expectation
    test_list.events.moving.emit.assert_called_once_with(0, 3)
    test_list.events.moved.emit.assert_called_once_with(0, 2, 0)
    test_list.events.reordered.emit.assert_called_once()

    test_list.events.moving.emit.reset_mock()
    test_list.move(2, 2)
    test_list.events.moving.emit.assert_not_called()  # noop

    # move the other way
    # pop the object at 3 and insert at current position 0
    assert test_list == [1, 2, 0, 3, 4]
    test_list.move(3, 0)
    assert test_list == [3, 1, 2, 0, 4]

    # negative index destination
    test_list.move(1, -2)
    assert test_list == [3, 2, 0, 1, 4]


BASIC_INDICES: List[tuple] = [
    ((2,), 0, [2, 0, 1, 3, 4, 5, 6, 7]),  # move single item
    ([0, 2, 3], 6, [1, 4, 5, 0, 2, 3, 6, 7]),  # move back
    ([4, 7], 1, [0, 4, 7, 1, 2, 3, 5, 6]),  # move forward
    ([0, 5, 6], 3, [1, 2, 0, 5, 6, 3, 4, 7]),  # move in between
    ([1, 3, 5, 7], 3, [0, 2, 1, 3, 5, 7, 4, 6]),  # same as above
    ([0, 2, 3, 2, 3], 6, [1, 4, 5, 0, 2, 3, 6, 7]),  # strip dupe indices
]
OTHER_INDICES: List[tuple] = [
    ([7, 4], 1, [0, 7, 4, 1, 2, 3, 5, 6]),  # move forward reorder
    ([3, 0, 2], 6, [1, 4, 5, 3, 0, 2, 6, 7]),  # move back reorder
    ((2, 4), -2, [0, 1, 3, 5, 6, 2, 4, 7]),  # negative indexing
    ([slice(None, 3)], 6, [3, 4, 5, 0, 1, 2, 6, 7]),  # move slice back
    ([slice(5, 8)], 2, [0, 1, 5, 6, 7, 2, 3, 4]),  # move slice forward
    ([slice(1, 8, 2)], 3, [0, 2, 1, 3, 5, 7, 4, 6]),  # move slice between
    ([slice(None, 8, 3)], 4, [1, 2, 0, 3, 6, 4, 5, 7]),
    ([slice(None, 8, 3), 0, 3, 6], 4, [1, 2, 0, 3, 6, 4, 5, 7]),
]
MOVING_INDICES = BASIC_INDICES + OTHER_INDICES


@pytest.mark.parametrize("sources, dest, expectation", MOVING_INDICES)
def test_move_multiple(sources, dest, expectation):
    """Test the that we can move objects with the move method"""
    el = EventedList(range(8))
    el.events = Mock(wraps=el.events)
    assert el == [0, 1, 2, 3, 4, 5, 6, 7]

    def _fail():
        raise AssertionError("unexpected event called")

    el.events.removing.connect(_fail)
    el.events.removed.connect(_fail)
    el.events.inserting.connect(_fail)
    el.events.inserted.connect(_fail)

    el.move_multiple(sources, dest)
    assert el == expectation
    el.events.moving.emit.assert_called()
    el.events.moved.emit.assert_called()
    el.events.reordered.emit.assert_called()


def test_move_multiple_mimics_slice_reorder():
    """Test the that move_multiple provides the same result as slice insertion."""
    data = list(range(8))
    el = EventedList(data)
    el.events = Mock(wraps=el.events)
    assert el == data
    new_order = [1, 5, 3, 4, 6, 7, 2, 0]
    # this syntax
    el.move_multiple(new_order, 0)
    # is the same as this syntax
    data[:] = [data[i] for i in new_order]
    assert el == new_order
    assert el == data
    assert el.events.moving.emit.call_args_list == [
        call(1, 0),
        call(5, 1),
        call(4, 2),
        call(5, 3),
        call(6, 4),
        call(7, 5),
        call(7, 6),
    ]
    assert el.events.moved.emit.call_args_list == [
        call(1, 0, 1),
        call(5, 1, 5),
        call(4, 2, 3),
        call(5, 3, 4),
        call(6, 4, 6),
        call(7, 5, 7),
        call(7, 6, 2),
    ]
    el.events.reordered.emit.assert_called()

    # move_multiple also works omitting the insertion index
    el[:] = list(range(8))
    expected = [el[i] for i in new_order]
    el.move_multiple(new_order)
    assert el == expected


def test_child_events():
    """Test that evented lists bubble child events."""
    # create a random object that emits events
    class E:
        test = Signal(str)

    e_obj = E()
    root: EventedList[E] = EventedList(child_events=True)
    mock = Mock()
    root.events.connect(mock)
    root.append(e_obj)
    assert len(e_obj.test) == 1
    assert root == [e_obj]
    e_obj.test.emit("hi")

    assert mock.call_count == 3

    expected = [
        call(EmissionInfo(root.events.inserting, (0,))),
        call(EmissionInfo(root.events.inserted, (0, e_obj))),
        call(EmissionInfo(root.events.child_event, (0, e_obj, e_obj.test, ("hi",)))),
    ]
    mock.assert_has_calls(expected)

    del root[0]
    assert len(e_obj.test) == 0


def test_child_events_groups():
    """Test that evented lists bubble child events."""
    # create a random object that emits events
    class Group(SignalGroup):
        test = Signal(str)
        test2 = Signal(str)

    class E:
        def __init__(self):
            self.events = Group(self)

    e_obj = E()
    root: EventedList[E] = EventedList(child_events=True)
    mock = Mock()
    root.events.connect(mock)
    root.append(e_obj)
    assert root == [e_obj]
    e_obj.events.test2.emit("hi")

    assert mock.call_count == 3

    # when an object in the list owns an emitter group, then any emitter in that group
    # will also be detected, and child_event will emit (index, sub-emitter, args)
    expected = [
        call(EmissionInfo(root.events.inserting, (0,))),
        call(EmissionInfo(root.events.inserted, (0, e_obj))),
        call(
            EmissionInfo(
                root.events.child_event, (0, e_obj, e_obj.events.test2, ("hi",))
            )
        ),
    ]

    # note that we can get back to the actual object in the list using the .instance
    # attribute on signal instances.
    assert e_obj.events.test2.instance.instance == e_obj
    mock.assert_has_calls(expected)
