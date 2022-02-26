from unittest.mock import Mock

from psygnal.containers._selection import Selection


def test_add_and_remove_from_selection():
    selection = Selection()
    selection.events._current = Mock()
    assert not selection._current
    assert not selection
    selection.add(1)
    selection._current = 1
    selection.events._current.emit.assert_called_once()

    assert 1 in selection
    assert selection._current == 1

    selection.remove(1)
    assert not selection


def test_selection_update_active_called_on_selection_change():
    selection = Selection()
    selection._update_active = Mock()
    selection.add(1)
    selection._update_active.assert_called_once()


def test_selection_active_event_emitted_on_selection_change():
    selection = Selection()
    selection.events.active = Mock()
    assert not selection.active
    selection.add(1)
    assert selection.active == 1
    selection.events.active.emit.assert_called_once()


def test_selection_current_setter():
    """Current event should only emit if value changes."""
    selection = Selection()
    selection._current = 1
    selection.events._current = Mock()
    selection._current = 1
    selection.events._current.emit.assert_not_called()
    selection._current = 2
    selection.events._current.emit.assert_called_once()
