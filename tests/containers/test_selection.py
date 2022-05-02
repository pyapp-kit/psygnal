from unittest.mock import Mock

from psygnal.containers import Selection


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


def test_update_active_called_on_selection_change():
    selection = Selection()
    selection._update_active = Mock()
    selection.add(1)
    selection._update_active.assert_called_once()


def test_active_event_emitted_on_selection_change():
    selection = Selection()
    selection.events.active = Mock()
    assert not selection.active
    selection.add(1)
    assert selection.active == 1
    selection.events.active.emit.assert_called_once()


def test_current_setter():
    """Current event should only emit if value changes."""
    selection = Selection()
    selection._current = 1
    selection.events._current = Mock()
    selection._current = 1
    selection.events._current.emit.assert_not_called()
    selection._current = 2
    selection.events._current.emit.assert_called_once()


def test_active_setter():
    """Active setter should make value the only selected item, make it current and
    emit the active event."""
    selection = Selection()
    selection.events.active = Mock()
    assert not selection._current
    selection.active = 1
    assert selection.active == 1
    assert selection._current == 1
    selection.events.active.emit.assert_called_once()


def test_select_only():
    selection = Selection([1, 2])
    selection.active = 1
    assert selection.active == 1
    selection.select_only(2)
    assert selection.active == 2


def test_clear():
    selection = Selection([1, 2])
    selection._current = 2
    assert len(selection) == 2
    selection.clear(keep_current=True)
    assert len(selection) == 0
    assert selection._current == 2
    selection.clear(keep_current=False)
    assert selection._current is None


def test_toggle():
    selection = Selection()
    selection.symmetric_difference_update = Mock()
    selection.toggle(1)
    selection.symmetric_difference_update.assert_called_once()


def test_emit_change():
    """emit change is overridden to also update the active value."""
    selection = Selection()
    selection._update_active = Mock()
    selection._emit_change((None), (None))
    selection._update_active.assert_called_once()


def test_hash():
    assert hash(Selection())
