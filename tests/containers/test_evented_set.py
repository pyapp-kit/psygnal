from unittest.mock import Mock, call

import pytest

from psygnal.containers import EventedOrderedSet, EventedSet, OrderedSet


@pytest.fixture
def regular_set():
    return set(range(5))


@pytest.fixture(params=[EventedSet, EventedOrderedSet])
def test_set(request, regular_set):
    return request.param(regular_set)


@pytest.mark.parametrize(
    "meth",
    [
        # METHOD, ARGS, EXPECTED EVENTS
        # primary interface
        ("add", 2, []),
        ("add", 10, [call((10,), ())]),
        ("discard", 2, [call((), (2,))]),
        ("remove", 2, [call((), (2,))]),
        ("discard", 10, []),
        # parity with set
        ("update", {3, 4, 5, 6}, [call((5, 6), ())]),
        ("difference_update", {3, 4, 5, 6}, [call((), (3, 4))]),
        ("intersection_update", {3, 4, 5, 6}, [call((), (0, 1, 2))]),
        ("symmetric_difference_update", {3, 4, 5, 6}, [call((5, 6), (3, 4))]),
    ],
    ids=lambda x: x[0],
)
def test_set_interface_parity(test_set: EventedSet, regular_set: set, meth):
    method_name, arg, expected = meth
    mock = Mock()

    test_set.events.items_changed.connect(mock)

    test_set_method = getattr(test_set, method_name)
    assert tuple(test_set) == tuple(regular_set)

    regular_set_method = getattr(regular_set, method_name)
    assert test_set_method(arg) == regular_set_method(arg)
    assert tuple(test_set) == tuple(regular_set)

    mock.assert_has_calls(expected)
    assert type(test_set).__name__ in repr(test_set)


def test_set_pop(test_set: EventedSet):
    mock = Mock()
    test_set.events.items_changed.connect(mock)

    npops = len(test_set)
    while test_set:
        test_set.pop()

    assert mock.call_count == npops

    with pytest.raises(KeyError):
        test_set.pop()
    with pytest.raises(KeyError):
        test_set.remove(34)


def test_set_clear(test_set: EventedSet):
    mock = Mock()
    test_set.events.items_changed.connect(mock)
    mock.assert_not_called()
    test_set.clear()
    mock.assert_called_once_with((), (0, 1, 2, 3, 4))


@pytest.mark.parametrize(
    "meth",
    [
        ("difference", {3, 4, 5, 6}),
        ("intersection", {3, 4, 5, 6}),
        ("issubset", {3, 4}),
        ("issubset", {3, 4, 5, 6}),
        ("issubset", {1, 2, 3, 4, 5, 6}),
        ("issuperset", {3, 4}),
        ("issuperset", {3, 4, 5, 6}),
        ("issuperset", {1, 2, 3, 4, 5, 6}),
        ("symmetric_difference", {3, 4, 5, 6}),
        ("union", {3, 4, 5, 6}),
    ],
)
def test_set_new_objects(test_set: EventedSet, regular_set: set, meth):
    method_name, arg = meth
    test_set_method = getattr(test_set, method_name)
    assert tuple(test_set) == tuple(regular_set)

    mock = Mock()
    test_set.events.items_changed.connect(mock)
    regular_set_method = getattr(regular_set, method_name)
    result = test_set_method(arg)
    assert result == regular_set_method(arg)
    assert isinstance(result, (EventedSet, EventedOrderedSet, bool))
    assert result is not test_set

    mock.assert_not_called()


def test_ordering():
    tup = (24, 16, 8, 4, 5, 6)
    s_tup = set(tup)
    os_tup = OrderedSet(tup)

    assert tuple(s_tup) != tup
    assert repr(s_tup) == "{4, 5, 6, 8, 16, 24}"

    assert tuple(os_tup) == tup
    assert repr(os_tup) == "OrderedSet((24, 16, 8, 4, 5, 6))"
    os_tup.discard(8)
    os_tup.add(8)
    assert tuple(os_tup) == (24, 16, 4, 5, 6, 8)


def test_copy(test_set):
    from copy import copy

    assert test_set.copy() == copy(test_set)
    assert test_set is not copy(test_set)
    assert isinstance(copy(test_set), type(test_set))


def test_repr(test_set):
    if isinstance(test_set, EventedOrderedSet):
        assert repr(test_set) == "EventedOrderedSet((0, 1, 2, 3, 4))"
    else:
        assert repr(test_set) == "EventedSet({0, 1, 2, 3, 4})"
