from unittest.mock import Mock

import pytest

from psygnal.containers import SelectableEventedList


@pytest.fixture
def regular_list():
    return list(range(5))


@pytest.fixture
def test_list(regular_list):
    test_list = SelectableEventedList(regular_list)
    test_list.events = Mock(wraps=test_list.events)
    return test_list


def test_select_item_not_in_list(test_list):
    """Items not in list should not be added to selection."""
    with pytest.raises(ValueError):
        test_list.selection.add(6)
    assert 6 not in test_list.selection


def test_newly_selected_item_is_active(test_list):
    """Items added to a selection should become active."""
    test_list.selection.clear()
    test_list.selection.add(1)
    assert test_list.selection.active == 1
