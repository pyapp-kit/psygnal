from unittest.mock import Mock

import pytest

from psygnal.containers import SelectableEventedList


@pytest.fixture
def regular_list() -> list:
    return list(range(5))


@pytest.fixture
def test_list(regular_list: list) -> SelectableEventedList:
    test_list = SelectableEventedList(regular_list)
    test_list.events = Mock(wraps=test_list.events)
    test_list.selection.events = Mock(wraps=test_list.selection.events)
    return test_list


def test_select_item_not_in_list(test_list: SelectableEventedList) -> None:
    """Items not in list should not be added to selection."""
    with pytest.raises(ValueError):
        test_list.selection.add(6)
    assert 6 not in test_list.selection


def test_newly_selected_item_is_active(test_list: SelectableEventedList) -> None:
    """Items added to a selection should become active."""
    test_list.selection.clear()
    test_list.selection.add(1)
    assert test_list.selection.active == 1


def test_select_all(test_list: SelectableEventedList) -> None:
    """Select all should populate the selection."""
    test_list.selection.update = Mock(wraps=test_list.selection.update)
    test_list.selection.clear()
    assert not test_list.selection
    test_list.select_all()
    assert all(el in test_list.selection for el in range(5))
    test_list.selection.update.assert_called_once()


def test_deselect_all(test_list: SelectableEventedList) -> None:
    """Deselect all should clear the selection"""
    test_list.selection.clear = Mock(wraps=test_list.selection.clear)
    test_list.selection = list(range(5))
    assert all(el in test_list.selection for el in range(5))
    test_list.deselect_all()
    assert not test_list.selection
    test_list.selection.clear.assert_called_once()


@pytest.mark.parametrize(
    "initial_selection, step, expand_selection, wraparound, expected",
    [
        ({0}, 1, False, False, {1}),
        ({0}, 2, False, False, {2}),
        ({0}, 2, True, False, {0, 2}),
        ({0, 1}, 1, False, False, {1}),
        ({0}, 5, False, False, {4}),
        ({0}, 5, False, True, {0}),
        ({}, 1, False, False, {4}),
    ],
)
def test_select_next(
    test_list: SelectableEventedList,
    initial_selection,
    step,
    expand_selection,
    wraparound,
    expected,
):
    """Test select next method behaviour."""
    test_list.selection = initial_selection
    test_list.select_next(
        step=step, expand_selection=expand_selection, wraparound=wraparound
    )
    assert test_list.selection == expected


def test_select_next_with_empty_list():
    """Selection should remain unchanged on advancing if list is empty."""
    test_list = SelectableEventedList([])
    initial_selection = test_list.selection.copy()
    test_list.select_next()
    assert test_list.selection == initial_selection


@pytest.mark.parametrize(
    "initial_selection, expand_selection, wraparound, expected",
    [
        ({1}, False, False, {0}),
        ({0}, False, False, {0}),
        ({1}, True, False, {0, 1}),
        ({1, 2}, False, False, {0}),
        ({0}, False, True, {4}),
    ],
)
def test_select_previous(
    test_list, initial_selection, expand_selection, wraparound, expected
):
    """Test select next method behaviour."""
    test_list.selection = initial_selection
    test_list.select_previous(expand_selection=expand_selection, wraparound=wraparound)
    assert test_list.selection == expected


def test_item_discarded_from_selection_on_removal_from_list(
    test_list: SelectableEventedList,
) -> None:
    """Check that items removed from a list are also removed from the selection."""
    test_list.selection.clear()
    test_list.selection.discard = Mock(wraps=test_list.selection.discard)
    test_list.selection = {0}
    assert 0 in test_list.selection
    test_list.remove(0)
    assert 0 not in test_list.selection
    test_list.selection.discard.assert_called_once()


def test_remove_selected(test_list: SelectableEventedList) -> None:
    """Test items are removed from both the selection and the list."""
    test_list.selection.clear()
    initial_selection = {0, 1}
    test_list.selection = initial_selection
    assert test_list.selection == initial_selection

    output = test_list.remove_selected()
    assert set(output) == initial_selection
    assert all(el not in test_list for el in initial_selection)
    assert all(el not in test_list.selection for el in initial_selection)
    assert test_list.selection == {2}
