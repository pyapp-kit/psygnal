import os
from copy import copy
from typing import Any, cast
from unittest.mock import Mock, call

import numpy as np
import pytest

from psygnal import EmissionInfo, PathStep, Signal, SignalGroup
from psygnal.containers import EventedList
from psygnal.containers._evented_list import _contiguous_runs


@pytest.fixture
def regular_list():
    return list(range(5))


@pytest.fixture
def test_list(regular_list):
    test_list = EventedList(regular_list)
    test_list.events = Mock(wraps=test_list.events)
    return test_list


# per-item events bracketed by the contiguous-block batch_* events
INSERT = ("batch_inserting", "inserting", "inserted", "batch_inserted")
REMOVE = ("batch_removing", "removing", "removed", "batch_removed")


def _remove_block(n: int) -> tuple[str, ...]:
    # one contiguous block of N removals:
    # batch_removing, (removing, removed)*N, batch_removed
    return ("batch_removing", *(("removing", "removed") * n), "batch_removed")


REMOVE_BLOCK2 = _remove_block(2)


@pytest.mark.parametrize(
    "meth",
    [
        # METHOD, ARGS, EXPECTED EVENTS
        # primary interface
        ("insert", (2, 10), INSERT),  # create
        ("__getitem__", (2,), ()),  # read
        ("__setitem__", (2, 3), ("changed",)),  # update
        ("__setitem__", (slice(2), [1, 2]), ("changed",)),  # update slice
        ("__setitem__", (slice(2, 2), [1, 2]), ("changed",)),  # update slice
        ("__delitem__", (2,), REMOVE),  # delete
        ("__delitem__", (slice(2),), REMOVE_BLOCK2),  # contiguous block
        ("__delitem__", (slice(0, 0),), ()),  # empty slice -> no emission
        ("__delitem__", (slice(-3),), REMOVE_BLOCK2),
        ("__delitem__", (slice(-2, None),), REMOVE_BLOCK2),
        # non-contiguous removal -> one bracketed block per contiguous run
        ("__delitem__", (slice(None, None, 2),), REMOVE * 3),
        # inherited interface
        ("append", (3,), INSERT),
        ("clear", (), _remove_block(5)),  # whole list removed as one block
        ("count", (3,), ()),
        (
            "extend",
            ([7, 8, 9],),
            ("batch_inserting", *(("inserting", "inserted") * 3), "batch_inserted"),
        ),
        ("index", (3,), ()),
        ("pop", (-2,), REMOVE),
        ("remove", (3,), REMOVE),
        ("reverse", (), ("reordered",)),
        ("__add__", ([7, 8, 9],), ()),  # operates on a copy
        (
            "__iadd__",
            ([7, 9],),
            ("batch_inserting", *(("inserting", "inserted") * 2), "batch_inserted"),
        ),
        ("__radd__", ([7, 9],), ()),  # does not mutate self
        # sort?
    ],
    ids=lambda x: x[0],
)
def test_list_interface_parity(test_list, regular_list, meth):
    method_name, args, expected = meth
    received: list[str] = []
    test_list.events.connect(lambda info: received.append(info.signal.name))

    test_list_method = getattr(test_list, method_name)
    assert tuple(test_list) == tuple(regular_list)
    if hasattr(regular_list, method_name):
        regular_list_method = getattr(regular_list, method_name)
        assert test_list_method(*args) == regular_list_method(*args)
        assert tuple(test_list) == tuple(regular_list)
    else:
        test_list_method(*args)  # smoke test

    assert tuple(received) == expected


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


def test_move(test_list: EventedList) -> None:
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


BASIC_INDICES: list[tuple] = [
    ((2,), 0, [2, 0, 1, 3, 4, 5, 6, 7]),  # move single item
    ([0, 2, 3], 6, [1, 4, 5, 0, 2, 3, 6, 7]),  # move back
    ([4, 7], 1, [0, 4, 7, 1, 2, 3, 5, 6]),  # move forward
    ([0, 5, 6], 3, [1, 2, 0, 5, 6, 3, 4, 7]),  # move in between
    ([1, 3, 5, 7], 3, [0, 2, 1, 3, 5, 7, 4, 6]),  # same as above
    ([0, 2, 3, 2, 3], 6, [1, 4, 5, 0, 2, 3, 6, 7]),  # strip dupe indices
]
OTHER_INDICES: list[tuple] = [
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
    root.events.all.connect(mock)
    root.append(e_obj)
    assert len(e_obj.test) == 1
    assert root == [e_obj]
    e_obj.test.emit("hi")

    # batch_inserting + inserting + inserted + batch_inserted + the child event
    assert mock.call_count == 5

    expected = [
        call(
            EmissionInfo(root.events.batch_inserting, (0, 1), path=(PathStep(index=0),))
        ),
        call(EmissionInfo(root.events.inserting, (0,), path=(PathStep(index=0),))),
        call(EmissionInfo(root.events.inserted, (0, e_obj), path=(PathStep(index=0),))),
        call(
            EmissionInfo(
                root.events.batch_inserted, (0, 1, [e_obj]), path=(PathStep(index=0),)
            )
        ),
        call(
            EmissionInfo(
                e_obj.test, ("hi",), path=(PathStep(index=0), PathStep(attr="test"))
            )
        ),
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
    root.events.all.connect(mock)
    root.append(e_obj)
    assert root == [e_obj]
    e_obj.events.test2.emit("hi")

    assert [c[0][0].signal.name for c in mock.call_args_list] == [
        "batch_inserting",
        "inserting",
        "inserted",
        "batch_inserted",
        "test2",  # This is now the direct child signal, not child_event
    ]

    # when an object in the list owns an emitter group, then any emitter in that group
    # will also be detected, and the child event will be emitted directly with path info
    expected = [
        call(
            EmissionInfo(root.events.batch_inserting, (0, 1), path=(PathStep(index=0),))
        ),
        call(EmissionInfo(root.events.inserting, (0,), path=(PathStep(index=0),))),
        call(EmissionInfo(root.events.inserted, (0, e_obj), path=(PathStep(index=0),))),
        call(
            EmissionInfo(
                root.events.batch_inserted, (0, 1, [e_obj]), path=(PathStep(index=0),)
            )
        ),
        call(EmissionInfo(e_obj.events.test2, ("hi",), path=(PathStep(index=0),))),
    ]

    # note that we can get back to the actual object in the list using the .instance
    # attribute on signal instances.
    assert e_obj.events.test2.instance.all.instance == e_obj
    mock.assert_has_calls(expected)


def test_copy_no_sync():
    l1 = EventedList([1, 2, 3])
    l2 = copy(l1)
    l1.append(4)
    assert len(l2) == 3


@pytest.mark.parametrize(
    "indices, expected",
    [
        ([], []),  # empty -> no runs
        ([3], [(3, 4)]),
        ([1, 2, 3], [(1, 4)]),  # single contiguous block
        ([3, 1, 2], [(1, 4)]),  # unsorted input
        ([1, 1, 2], [(1, 3)]),  # duplicates collapsed
        ([0, 2, 4], [(4, 5), (2, 3), (0, 1)]),  # non-contiguous, highest first
        ([1, 2, 3, 5, 6], [(5, 7), (1, 4)]),
    ],
)
def test_contiguous_runs(indices: list[int], expected: list[tuple[int, int]]) -> None:
    assert list(_contiguous_runs(indices)) == expected


def test_batch_inserted_emits_once_for_batch():
    """The batch_* signals fire once per contiguous block; per-item N times."""
    el = EventedList([0, 1, 2])
    batch_inserting = Mock()
    batch_inserted = Mock()
    inserted = Mock()
    el.events.batch_inserting.connect(batch_inserting)
    el.events.batch_inserted.connect(batch_inserted)
    el.events.inserted.connect(inserted)

    el.extend([3, 4, 5])
    assert el == [0, 1, 2, 3, 4, 5]
    # batch signal fires exactly once over the whole contiguous range...
    batch_inserting.assert_called_once_with(3, 6)
    batch_inserted.assert_called_once_with(3, 6, [3, 4, 5])
    # ...while the per-item signal still fires once per item (unchanged contract)
    assert inserted.call_args_list == [call(3, 3), call(4, 4), call(5, 5)]

    # a single insert is just a length-1 range
    batch_inserting.reset_mock()
    batch_inserted.reset_mock()
    el.insert(0, 99)
    batch_inserting.assert_called_once_with(0, 1)
    batch_inserted.assert_called_once_with(0, 1, [99])


def test_per_item_signals_unchanged():
    """Legacy (index)/(index, value) callbacks behave exactly as before."""
    el = EventedList([0, 1, 2])
    inserting = Mock()
    inserted = Mock()
    removed = Mock()
    el.events.inserting.connect(inserting)
    el.events.inserted.connect(inserted)
    el.events.removed.connect(removed)

    el.append(9)
    inserting.assert_called_once_with(3)
    inserted.assert_called_once_with(3, 9)

    # a batch still emits the per-item event for *every* item, not just once
    inserting.reset_mock()
    inserted.reset_mock()
    el.extend([10, 11])
    assert inserting.call_args_list == [call(4), call(5)]
    assert inserted.call_args_list == [call(4, 10), call(5, 11)]

    del el[0]
    removed.assert_called_once_with(0, 0)


@pytest.mark.parametrize("index", [-100, -2, -1, 0, 1, 2, 100])
def test_insert_index_parity(index):
    """insert() with negative/out-of-range indices matches builtin list."""
    el = EventedList([0, 1, 2])
    ref = [0, 1, 2]
    el.insert(index, 9)
    ref.insert(index, 9)
    assert el == ref


def test_batch_removed_emits_per_block():
    """Contiguous removals emit one block; non-contiguous emit once per block."""
    el = EventedList([0, 1, 2, 3, 4, 5])
    batch_removing = Mock()
    batch_removed = Mock()
    el.events.batch_removing.connect(batch_removing)
    el.events.batch_removed.connect(batch_removed)

    # contiguous slice -> single block
    del el[1:4]
    assert el == [0, 4, 5]
    batch_removing.assert_called_once_with(1, 4)
    batch_removed.assert_called_once_with(1, 4, [1, 2, 3])

    # non-contiguous slice -> one block per contiguous run, highest first
    el[:] = [0, 1, 2, 3, 4, 5]
    batch_removing.reset_mock()
    batch_removed.reset_mock()
    del el[::2]  # indices 0, 2, 4
    assert el == [1, 3, 5]
    assert batch_removing.call_args_list == [call(4, 5), call(2, 3), call(0, 1)]
    assert batch_removed.call_args_list == [
        call(4, 5, [4]),
        call(2, 3, [2]),
        call(0, 1, [0]),
    ]


def test_clear_emits_single_block():
    """clear() removes the whole list as one bracketed block."""
    el = EventedList([0, 1, 2, 3])
    batch_removing = Mock()
    batch_removed = Mock()
    removed = Mock()
    el.events.batch_removing.connect(batch_removing)
    el.events.batch_removed.connect(batch_removed)
    el.events.removed.connect(removed)

    el.clear()
    assert el == []
    batch_removing.assert_called_once_with(0, 4)
    batch_removed.assert_called_once_with(0, 4, [0, 1, 2, 3])
    # per-item still fires for each, highest index first (unchanged from before)
    assert removed.call_args_list == [call(3, 3), call(2, 2), call(1, 1), call(0, 0)]


def test_batch_signals_drive_qt_style_model():
    """batch_* (start, stop) ranges wire directly onto begin/end{Insert,Remove}Rows."""
    el = EventedList([0, 1, 2])
    calls: list[tuple] = []

    el.events.batch_inserting.connect(
        lambda start, stop: calls.append(("beginInsertRows", start, stop - 1))
    )
    el.events.batch_inserted.connect(lambda *_: calls.append(("endInsertRows",)))
    el.events.batch_removing.connect(
        lambda start, stop: calls.append(("beginRemoveRows", start, stop - 1))
    )
    el.events.batch_removed.connect(lambda *_: calls.append(("endRemoveRows",)))

    el.extend([3, 4])  # a single bracketed block for the whole batch
    del el[0:2]

    assert calls == [
        ("beginInsertRows", 3, 4),  # inclusive last row, as Qt expects
        ("endInsertRows",),
        ("beginRemoveRows", 0, 1),
        ("endRemoveRows",),
    ]


def test_subclass_insert_override_still_called_by_extend():
    """`extend`/`+=`/`__init__` must keep funneling through the public `insert`."""

    class MyList(EventedList):
        def __init__(self, *args, **kwargs):
            self.seen: list[tuple[int, Any]] = []
            super().__init__(*args, **kwargs)

        def insert(self, index: int, value: Any) -> None:
            self.seen.append((index, value))
            super().insert(index, value)

    el = MyList([0, 1])  # __init__ extends
    assert el.seen == [(0, 0), (1, 1)]

    el.extend([2, 3])
    assert el.seen[-2:] == [(2, 2), (3, 3)]

    el += [4]
    assert el.seen[-1] == (4, 4)
    assert el == [0, 1, 2, 3, 4]


def test_insert_emits_nothing_if_pre_insert_raises():
    """A rejected value must not leave an unterminated `batch_inserting` behind."""

    class Validated(EventedList):
        def _pre_insert(self, value: Any) -> Any:
            if not isinstance(value, int):
                raise TypeError("ints only")
            return value

    el = Validated([0, 1])
    received: list[str] = []
    el.events.connect(lambda info: received.append(info.signal.name))

    with pytest.raises(TypeError, match="ints only"):
        el.insert(1, "nope")
    assert received == []  # not even batch_inserting
    assert el == [0, 1]

    # and the batch signals stay paired on the success path
    el.insert(1, 9)
    assert tuple(received) == INSERT
    assert el == [0, 9, 1]
