from collections.abc import MutableSequence
from unittest.mock import Mock, call

import numpy as np
import pytest

from psygnal import Signal
from psygnal.containers import EventedList


@pytest.fixture
def regular_list():
    return list(range(5))


@pytest.fixture(params=[EventedList])
def test_list(request, regular_list):
    test_list = request.param(regular_list)
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


def test_hash(test_list):
    assert id(test_list) == hash(test_list)


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


def test_move(test_list):
    """Test the that we can move objects with the move method"""
    test_list.events = Mock(wraps=test_list.events)

    def _fail():
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
    test_list.events.moving.assert_called_once()
    test_list.events.moved.assert_called_once()
    test_list.events.reordered.assert_called_with(value=expectation)

    # move the other way
    # pop the object at 3 and insert at current position 0
    assert test_list == [1, 2, 0, 3, 4]
    test_list.move(3, 0)
    assert test_list == [3, 1, 2, 0, 4]

    # negative index destination
    test_list.move(1, -2)
    assert test_list == [3, 2, 0, 1, 4]


BASIC_INDICES = [
    ((2,), 0, [2, 0, 1, 3, 4, 5, 6, 7]),  # move single item
    ([0, 2, 3], 6, [1, 4, 5, 0, 2, 3, 6, 7]),  # move back
    ([4, 7], 1, [0, 4, 7, 1, 2, 3, 5, 6]),  # move forward
    ([0, 5, 6], 3, [1, 2, 0, 5, 6, 3, 4, 7]),  # move in between
    ([1, 3, 5, 7], 3, [0, 2, 1, 3, 5, 7, 4, 6]),  # same as above
    ([0, 2, 3, 2, 3], 6, [1, 4, 5, 0, 2, 3, 6, 7]),  # strip dupe indices
]
OTHER_INDICES = [
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


@pytest.mark.parametrize("sources,dest,expectation", MOVING_INDICES)
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
    el.events.moving.assert_called()
    el.events.moved.assert_called()
    el.events.reordered.assert_called_with(value=expectation)


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
    assert el.events.moving.call_args_list == [
        call(index=1, new_index=0),
        call(index=5, new_index=1),
        call(index=4, new_index=2),
        call(index=5, new_index=3),
        call(index=6, new_index=4),
        call(index=7, new_index=5),
        call(index=7, new_index=6),
    ]
    assert el.events.moved.call_args_list == [
        call(index=1, new_index=0, value=1),
        call(index=5, new_index=1, value=5),
        call(index=4, new_index=2, value=3),
        call(index=5, new_index=3, value=4),
        call(index=6, new_index=4, value=6),
        call(index=7, new_index=5, value=7),
        call(index=7, new_index=6, value=2),
    ]
    el.events.reordered.assert_called_with(value=new_order)

    # move_multiple also works omitting the insertion index
    el[:] = list(range(8))
    el.move_multiple(new_order) == [el[i] for i in new_order]


def test_slice(test_list, regular_list):
    """Slicing an evented list should return a same-class evented list."""
    test_slice = test_list[1:3]
    regular_slice = regular_list[1:3]
    assert tuple(test_slice) == tuple(regular_slice)
    assert isinstance(test_slice, test_list.__class__)


NEST = [0, [10, [110, [1110, 1111, 1112], 112], 12], 2]


def flatten(container):
    """Flatten arbitrarily nested list.

    Examples
    --------
    >>> a = [1, [2, [3], 4], 5]
    >>> list(flatten(a))
    [1, 2, 3, 4, 5]
    """
    for i in container:
        if isinstance(i, MutableSequence):
            yield from flatten(i)
        else:
            yield i


class E:
    test = Signal(str)


def test_child_events():
    """Test that evented lists bubble child events."""
    # create a random object that emits events
    e_obj = E()
    # and two nestable evented lists
    root: EventedList[str] = EventedList()
    observed = []
    root.events.connect(lambda e: observed.append(e))
    root.append(e_obj)
    e_obj.test.emit("hi")
    obs = [(e.type, e.index, getattr(e, "value", None)) for e in observed]
    expected = [
        ("inserting", 0, None),  # before we inserted b into root
        ("inserted", 0, e_obj),  # after b was inserted into root
        ("test", 0, "hi"),  # when e_obj emitted an event called "test"
    ]
    for o, e in zip(obs, expected):
        assert o == e


def test_evented_list_subclass():
    """Test that multiple inheritance maintains events from superclass."""

    class A:
        boom = Signal()

    class B(A, EventedList):
        pass

    lst = B([1, 2])
    assert hasattr(lst, "events")
    assert "boom" in lst.events.emitters
    assert lst == [1, 2]


def test_array_like_setitem():
    """Test that EventedList.__setitem__ works for array-like items"""
    array = np.array((10, 10))
    evented_list = EventedList([array])
    evented_list[0] = array
