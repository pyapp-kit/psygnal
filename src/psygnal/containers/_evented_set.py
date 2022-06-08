from __future__ import annotations

from enum import Enum
from itertools import chain
from typing import Any, Dict, Iterable, Iterator, MutableSet, Set, Tuple, TypeVar, Union

from typing_extensions import Final, Literal

from psygnal import Signal, SignalGroup

_T = TypeVar("_T")
_Cls = TypeVar("_Cls", bound="_BaseMutableSet")


class _BAIL(Enum):
    BAIL = 0


BAIL: Final = _BAIL.BAIL
BailType = Literal[_BAIL.BAIL]


class _BaseMutableSet(MutableSet[_T]):
    _data: Set[_T]  # pragma: no cover

    def __init__(self, iterable: Iterable[_T] = ()):
        self._data = set()
        self._data.update(iterable)

    def add(self, item: _T) -> None:
        """Add an element to a set.

        This has no effect if the element is already present.
        """
        _item = self._pre_add_hook(item)
        if _item is not BAIL:
            self._do_add(_item)
            self._post_add_hook(_item)

    def update(self, *others: Iterable[_T]) -> None:
        """Update this set with the union of this set and others."""
        for i in chain(*others):
            self.add(i)

    def discard(self, item: _T) -> None:
        """Remove an element from a set if it is a member.

        If the element is not a member, do nothing.
        """
        _item = self._pre_discard_hook(item)
        if _item is not BAIL:
            self._do_discard(_item)
            self._post_discard_hook(_item)

    def __contains__(self, value: object) -> bool:
        """Return True if value is in set."""
        return value in self._data

    def __iter__(self) -> Iterator[_T]:
        """Implement iter(self)."""
        return iter(self._data)

    def __len__(self) -> int:
        """Return len(self)."""
        return len(self._data)

    def __repr__(self) -> str:
        """Return repr(self)."""
        return f"{self.__class__.__name__}({self._data!r})"

    # --------

    def _pre_add_hook(self, item: _T) -> Union[_T, BailType]:
        return item  # pragma: no cover

    def _post_add_hook(self, item: _T) -> None:
        ...  # pragma: no cover

    def _pre_discard_hook(self, item: _T) -> Union[_T, BailType]:
        return item  # pragma: no cover

    def _post_discard_hook(self, item: _T) -> None:
        ...  # pragma: no cover

    def _do_add(self, item: _T) -> None:
        self._data.add(item)

    def _do_discard(self, item: _T) -> None:
        self._data.discard(item)

    # -------- To match set API

    def __copy__(self: _Cls) -> _Cls:
        inst = self.__class__.__new__(self.__class__)
        inst.__dict__.update(self.__dict__)
        return inst

    def copy(self: _Cls) -> _Cls:
        return self.__class__(self)

    def difference(self: _Cls, *s: Iterable[_T]) -> _Cls:
        """Return the difference of two or more sets as a new set.

        (i.e. all elements that are in this set but not the others.)
        """
        other = set(chain(*s))
        return self.__class__(i for i in self if i not in other)

    def difference_update(self, *s: Iterable[_T]) -> None:
        """Remove all elements of another set from this set."""
        for i in chain(*s):
            self.discard(i)

    def intersection(self: _Cls, *s: Iterable[_T]) -> _Cls:
        """Return the intersection of two sets as a new set.

        (i.e. all elements that are in both sets.)
        """
        other = set.intersection(*(set(x) for x in s))
        return self.__class__(i for i in self if i in other)

    def intersection_update(self, *s: Iterable[_T]) -> None:
        """Update this set with the intersection of itself and another."""
        other = set.intersection(*(set(x) for x in s))
        for i in tuple(self):
            if i not in other:
                self.discard(i)

    def issubset(self, __s: Iterable[Any]) -> bool:
        """Report whether another set contains this set."""
        return set(self).issubset(__s)

    def issuperset(self, __s: Iterable[Any]) -> bool:
        """Report whether this set contains another set."""
        return set(self).issuperset(__s)

    def symmetric_difference(self: _Cls, __s: Iterable[_T]) -> _Cls:
        """Return the symmetric difference of two sets as a new set.

        (i.e. all elements that are in exactly one of the sets.)
        """
        a = chain((i for i in __s if i not in self), (i for i in self if i not in __s))
        return self.__class__(a)

    def symmetric_difference_update(self, __s: Iterable[_T]) -> None:
        """Update this set with the symmetric difference of itself and another.

        This will remove any items in this set that are also in `other`, and
        add any items in others that are not present in this set.
        """
        for i in __s:
            self.discard(i) if i in self else self.add(i)

    def union(self: _Cls, *s: Iterable[_T]) -> _Cls:
        """Return the union of sets as a new set.

        (i.e. all elements that are in either set.)
        """
        new = self.copy()
        new.update(*s)
        return new


class OrderedSet(_BaseMutableSet[_T]):
    """A set that preserves insertion order, uses dict behind the scenes."""

    _data: Dict[_T, None]  # type: ignore  # pragma: no cover

    def __init__(self, iterable: Iterable[_T] = ()):
        self._data = {}
        self.update(iterable)

    def _do_add(self, item: _T) -> None:
        self._data[item] = None

    def _do_discard(self, item: _T) -> None:
        self._data.pop(item, None)

    def __repr__(self) -> str:
        """Return repr(self)."""
        inner = ", ".join(str(x) for x in self._data)
        return f"{self.__class__.__name__}(({inner}))"


class SetEvents(SignalGroup):
    """Events available on [EventedSet][psygnal.containers.EventedSet].

    Attributes
    ----------
    items_changed (added: Tuple[Any, ...], removed: Tuple[Any, ...])
        A signal that will emitted whenever an item or items are added or removed.
        Connected callbacks will be called with `callback(added, removed)`, where
        `added` and `removed` are tuples containing the objects that have been
        added or removed from the set.
    """

    items_changed = Signal(tuple, tuple)


class EventedSet(_BaseMutableSet[_T]):
    """A set with an `items_changed` signal that emits when items are added/removed.

    Parameters
    ----------
    iterable : Iterable[_T]
        Data to populate the set.  If omitted, an empty set is created.

    Attributes
    ----------
    events : SetEvents
        SignalGroup that with events related to set mutation.  (see SetEvents)

    Examples
    --------
    >>> from psygnal.containers import EventedSet
    >>>
    >>> my_set = EventedSet([1, 2, 3])
    >>> my_set.events.items_changed.connect(
    >>>     lambda a, r: print(f"added={a}, removed={r}")
    >>> )
    >>> my_set.update({3, 4, 5})
    added=(4, 5), removed=()

    Multi-item events will be reduced into a single emission:
    >>> my_set.symmetric_difference_update({4, 5, 6, 7})
    added=(6, 7), removed=(4, 5)

    >>> my_set
    EventedSet({1, 2, 3, 6, 7})
    """

    events: SetEvents  # pragma: no cover

    def __init__(self, iterable: Iterable[_T] = ()):
        self.events = self._get_events_class()
        super().__init__(iterable)

    def update(self, *others: Iterable[_T]) -> None:
        """Update this set with the union of this set and others."""
        with self.events.items_changed.paused(_reduce_events, ((), ())):
            super().update(*others)

    def clear(self) -> None:
        """Remove all elements from this set."""
        with self.events.items_changed.paused(_reduce_events, ((), ())):
            super().clear()

    def difference_update(self, *s: Iterable[_T]) -> None:
        """Remove all elements of another set from this set."""
        with self.events.items_changed.paused(_reduce_events, ((), ())):
            super().difference_update(*s)

    def intersection_update(self, *s: Iterable[_T]) -> None:
        """Update this set with the intersection of itself and another."""
        with self.events.items_changed.paused(_reduce_events, ((), ())):
            super().intersection_update(*s)

    def symmetric_difference_update(self, __s: Iterable[_T]) -> None:
        """Update this set with the symmetric difference of itself and another.

        This will remove any items in this set that are also in `other`, and
        add any items in others that are not present in this set.
        """
        with self.events.items_changed.paused(_reduce_events, ((), ())):
            super().symmetric_difference_update(__s)

    def _pre_add_hook(self, item: _T) -> Union[_T, BailType]:
        return BAIL if item in self else item

    def _post_add_hook(self, item: _T) -> None:
        self._emit_change((item,), ())

    def _pre_discard_hook(self, item: _T) -> Union[_T, BailType]:
        return BAIL if item not in self else item

    def _post_discard_hook(self, item: _T) -> None:
        self._emit_change((), (item,))

    def _emit_change(self, added: Tuple[_T, ...], removed: Tuple[_T, ...]) -> None:
        """Emit a change event."""
        self.events.items_changed.emit(added, removed)

    def _get_events_class(self) -> SetEvents:
        return SetEvents()


class EventedOrderedSet(EventedSet, OrderedSet[_T]):
    """A ordered variant of EventedSet that maintains insertion order.

    Parameters
    ----------
    iterable : Iterable[_T]
        Data to populate the set.  If omitted, an empty set is created.

    Attributes
    ----------
    events : SetEvents
        SignalGroup that with events related to set mutation.  (see SetEvents)
    """

    # reproducing init here to avoid a mkdocs warning:
    # "Parameter 'iterable' does not appear in the function signature"
    def __init__(self, iterable: Iterable[_T] = ()):
        super().__init__(iterable)


def _reduce_events(a: Tuple, b: Tuple) -> Tuple[tuple, tuple]:
    """Combine two events (a and b) each of which contain (added, removed)."""
    a0, a1 = a
    b0, b1 = b
    return (a0 + b0, a1 + b1)
