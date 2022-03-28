"""MutableSequence with a selection model."""
from typing import TypeVar

from ._evented_list import EventedList
from ._selection import Selectable

_T = TypeVar("_T")


class SelectableEventedList(Selectable[_T], EventedList[_T]):
    """List object with a built in selection model."""

    def __init__(self, *args, **kwargs) -> None:
        self._activate_on_insert: bool = True
        super().__init__(*args, **kwargs)
        self.events.removed.connect(self.selection.discard)
        self.selection._pre_add_hook = self._pre_select_hook

    def _pre_select_hook(self, value: _T) -> _T:
        """Called before adding an item to the selection."""
        if value not in self:
            raise ValueError("Cannot select an item that is not in the list.")
        return value

    def insert(self, index: int, value: _T) -> None:
        """Insert item(s) into the list and update the selection."""
        super().insert(index, value)
        if self._activate_on_insert:
            self.selection.active = value

    def select_all(self) -> None:
        """Select all items in the list."""
        self.selection.update(self)

    def deselect_all(self) -> None:
        """Deselect all items in the list."""
        self.selection.clear()

    def select_next(
        self, step: int = 1, expand_selection: bool = False, wraparound: bool = False
    ) -> None:
        """Select the next item in the list."""
        if self.selection._current is None and len(self) > 0:
            self.selection.active = self[-1 if step > 0 else 0]
            return
        idx = self.index(self.selection._current) + step
        if wraparound:
            idx = idx % len(self)
        next_item = self[idx]
        if expand_selection:
            self.selection.add(next_item)
            self.selection._current = next_item
        else:
            self.selection.active = next_item

    def select_previous(self, expand_selection: bool = False) -> None:
        """Select the previous item in the list."""
        self.select_next(step=-1, expand_selection=expand_selection)

    def remove_selected(self) -> None:
        """Remove selected items from the list."""
        idx = 0
        for item in list(self.selection):
            idx = self.index(item)
            self.remove(item)
        new_idx = max(0, idx - 1)
        if len(self) > new_idx:
            self.selection.add(self[new_idx])
