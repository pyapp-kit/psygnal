"""MutableSequence with a selection model."""
from typing import Tuple, TypeVar

from ._evented_list import EventedList
from ._selection import Selectable

_T = TypeVar("_T")


class SelectableEventedList(Selectable[_T], EventedList[_T]):
    """List object with a built in selection model."""

    def __init__(self, *args: _T, **kwargs: _T) -> None:
        self._activate_on_insert: bool = True
        super().__init__(*args, **kwargs)
        self.events.removed.connect(self.selection.discard)

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
        if len(self) == 0:
            return
        elif not self.selection and len(self) > 0:
            idx = -1 if step > 0 else 0
        else:
            idx = self.index(self.selection._current) + step
        idx_in_sequence = len(self) > idx >= 0
        if wraparound:
            idx = idx % len(self)
        elif not idx_in_sequence:
            idx = -1 if step > 0 else 0
        next_item = self[idx]
        if expand_selection:
            self.selection.add(next_item)
            self.selection._current = next_item
        else:
            self.selection.active = next_item

    def select_previous(
        self, expand_selection: bool = False, wraparound: bool = False
    ) -> None:
        """Select the previous item in the list."""
        self.select_next(
            step=-1, expand_selection=expand_selection, wraparound=wraparound
        )

    def remove_selected(self) -> Tuple[_T, ...]:
        """Remove selected items from the list and the selection."""
        selected_items = tuple(self.selection)
        idx = 0
        for item in list(self.selection):
            idx = self.index(item)
            self.remove(item)
            # shouldn't be necessary but remove is not discarding from selection
            # when called from here...
            self.selection.discard(item)
        new_idx = max(0, idx - 1)
        if len(self) > new_idx:
            self.selection.add(self[new_idx])
        return selected_items
