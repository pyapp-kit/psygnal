from typing import TYPE_CHECKING, Generic, Set, TypeVar

from .._group import SignalGroup
from .._signal import Signal
from ._evented_set import EventedSet

if TYPE_CHECKING:
    from typing import Iterable, Optional

_T = TypeVar("_T")
_S = TypeVar("_S")


class SelectionEvents(SignalGroup):
    """Events available on a Selection.

    Attributes
    ----------
    items_changed (added: Tuple[_T], removed: Tuple[_T])
        A signal that will emitted whenever an item or items are added or removed.
        Connected callbacks will be called with `callback(added, removed)`, where
        `added` and `removed` are tuples containing the objects that have been
        added or removed from the set.
    active (value: _T)
        emitted when the current item has changed.
    _current (value: _T)
        emitted when the current item has changed. (Private event)
    """

    items_changed = Signal(tuple, tuple)
    active = Signal(object)
    _current = Signal(object)


class Selection(EventedSet[_T]):
    """An model of selected items, with a `active` and `current` item.

    There can only be one `active` and one `current` item, but there can be
    multiple selected items.  An "active" item is defined as a single selected
    item (if multiple items are selected, there is no active item).  The
    "current" item is mostly useful for (e.g.) keyboard actions: even with
    multiple items selected, you may only have one current item, and keyboard
    events (like up and down) can modify that current item.  It's possible to
    have a current item without an active item, but an active item will always
    be the current item.
    An item can be the current item and selected at the same time. Qt views
    will ensure that there is always a current item as keyboard navigation,
    for example, requires a current item.
    This pattern mimics current/selected items from Qt:
    https://doc.qt.io/qt-5/model-view-programming.html#current-item-and-selected-items

    Parameters
    ----------
    data : iterable, optional
        Elements to initialize the set with.

    Attributes
    ----------
    active : Any, optional
        The active item, if any.  An active item is the one being edited.
    _current : Any, optional
        The current item, if any.  This is used primarily by GUI views when
        handling mouse/key events.
    """

    events: SelectionEvents

    def __init__(self, data: Iterable[_T] = ()):
        self._active: Optional[_T] = None
        self._current_: Optional[_T] = None
        super().__init__(iterable=data)
        self._update_active()

    def __repr__(self) -> str:
        return f"{type(self).__name__}({repr(self._data)})"

    def __hash__(self) -> int:
        """Make selection hashable."""
        return id(self)

    @property
    def _current(self) -> Optional[_T]:
        """Get current item."""
        return self._current_

    @_current.setter
    def _current(self, value: Optional[_T]) -> None:
        """Set current item."""
        if value == self._current_:
            return
        self._current_ = value
        self.events._current.emit(value)

    @property
    def active(self) -> Optional[_T]:
        """Return the currently active item or None."""
        return self._active

    @active.setter
    def active(self, value: Optional[_T]) -> None:
        """Set the active item.

        This makes `value` the only selected item, and makes it current.
        """
        if value == self._active:
            return
        self._active = value
        self.clear() if value is None else self.select_only(value)
        self._current = value
        self.events.active.emit(value)

    def _update_active(self) -> None:
        """On a selection event, update the active item based on selection.

        An active item is a single selected item.
        """
        if len(self) == 1:
            self.active = list(self)[0]
        elif self._active is not None:
            self._active = None
            self.events.active.emit(None)

    def clear(self, keep_current: bool = False) -> None:
        """Clear the selection."""
        if not keep_current:
            self._current = None
        super().clear()

    def toggle(self, obj: _T) -> None:
        """Toggle selection state of obj."""
        self.symmetric_difference_update({obj})

    def select_only(self, obj: _T) -> None:
        """Unselect everything but `obj`. Add to selection if not present."""
        self.intersection_update({obj})
        self.add(obj)

    def _get_events_class(self) -> SelectionEvents:
        """Override SetEvents with SelectionEvents."""
        return SelectionEvents()

    def _emit_change(self, added: Tuple[_T, ...], removed: Tuple[_T, ...]) -> None:
        """Emit a change event."""
        super()._emit_change(added, removed)
        self._update_active()


class Selectable(Generic[_S]):
    """Mixin that adds a selection model to an object."""

    def __init__(self, *args, **kwargs) -> None:  # type: ignore
        self._selection: Selection[_S] = Selection()
        super().__init__(*args, **kwargs)

    @property
    def selection(self) -> Selection[_S]:
        """Get current selection."""
        return self._selection

    @selection.setter
    def selection(self, new_selection: Iterable[_S]) -> None:
        """Set selection, without deleting selection model object."""
        self._selection.intersection_update(new_selection)
        self._selection.update(new_selection)
