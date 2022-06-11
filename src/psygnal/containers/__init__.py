"""Containers backed by psygnal events."""
from typing import TYPE_CHECKING, Any

from ._evented_dict import EventedDict
from ._evented_list import EventedList
from ._evented_set import EventedOrderedSet, EventedSet, OrderedSet
from ._selectable_evented_list import SelectableEventedList
from ._selection import Selection

if TYPE_CHECKING:
    from ._evented_proxy import EventedCallableObjectProxy, EventedObjectProxy

__all__ = [
    "EventedCallableObjectProxy",
    "EventedDict",
    "EventedList",
    "EventedObjectProxy",
    "EventedOrderedSet",
    "EventedSet",
    "OrderedSet",
    "SelectableEventedList",
    "Selection",
]


def __getattr__(name: str) -> Any:
    if name == "EventedObjectProxy":
        from ._evented_proxy import EventedObjectProxy

        return EventedObjectProxy
    if name == "EventedCallableObjectProxy":
        from ._evented_proxy import EventedCallableObjectProxy

        return EventedCallableObjectProxy
    raise AttributeError(  # pragma: no cover
        f"module {__name__!r} has no attribute {name!r}"
    )
