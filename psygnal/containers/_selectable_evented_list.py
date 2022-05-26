"""MutableSequence with a selection model."""
from typing import Any, Iterable, Tuple, TypeVar

from ._evented_list import EventedList, ListEvents
from ._selection import Selectable

_T = TypeVar("_T")


class SelectableEventedList(Selectable[_T], EventedList[_T]):
    """`EventedList` subclass with a built in selection model.

    In addition to all `EventedList` properties, this class also has a `selection`
    attribute that manages a set of selected items in the list.

    Parameters
    ----------
    data : iterable, optional
        Elements to initialize the list with.
    hashable : bool
        Whether the list should be hashable as id(self). By default `True`.
    child_events: bool
        Whether to re-emit events from emitted from evented items in the list
        (i.e. items that have SignalInstances). If `True`, child events can be connected
        at `EventedList.events.child_event`. By default, `False`.

    Attributes
    ----------
    events : ListEvents
        SignalGroup that with events related to list mutation.  (see ListEvents)
    selection : Selection
        An evented set containing the currently selected items, along with an `active`
        and `current` item.  (See `Selection`)
    """

    events: ListEvents  # pragma: no cover

    def __init__(
        self,
        data: Iterable[_T] = (),
        *,
        hashable: bool = True,
        child_events: bool = False,
    ):
        self._activate_on_insert: bool = True
        super().__init__(data=data, hashable=hashable, child_events=child_events)
        self.events.removed.connect(self._on_item_removed)

    def _on_item_removed(self, idx: int, obj: Any) -> None:
        self.selection.discard(obj)

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
        """Select the next item in the list.

        Parameters
        ----------
        step : int
            The step size to take when picking the next item, by default 1
        expand_selection : bool
            If True, will expand the selection to contain the both the current item and
            the next item, by default False
        wraparound : bool
            Whether to return to the beginning of the list of the end has been reached,
            by default False
        """
        if len(self) == 0:
            return
        elif not self.selection:
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
        """Remove selected items from the list and the selection.

        Returns
        -------
        Tuple[_T, ...]
            The items that were removed.
        """
        selected_items = tuple(self.selection)
        idx = 0
        for item in list(self.selection):
            idx = self.index(item)
            self.remove(item)
        new_idx = max(0, idx - 1)
        if len(self) > new_idx:
            self.selection.add(self[new_idx])
        return selected_items
