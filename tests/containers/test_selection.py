from unittest.mock import Mock

from psygnal.containers._selection import Selection


def test_selection():
    sel = Selection()
    sel.events._current = Mock()
    assert not sel._current
    assert not sel
    sel.add(1)
    sel._current = 1
    sel.events._current.emit.assert_called_once()

    assert 1 in sel
    assert sel._current == 1

    sel.remove(1)
    assert not sel
