"""Containers backed by psygnal events."""
from typing import Any

from ._evented_list import EventedList
from ._evented_set import EventedOrderedSet, EventedSet, OrderedSet
from ._selection import Selection

__all__ = [
    "EventedList",
    "EventedObjectProxy",
    "EventedOrderedSet",
    "EventedSet",
    "OrderedSet",
    "Selection",
]


def __getattr__(name: str) -> Any:
    if name == "EventedObjectProxy":
        from ._evented_proxy import EventedObjectProxy

        return EventedObjectProxy
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
