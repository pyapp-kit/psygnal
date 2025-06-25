"""Containers backed by psygnal events.

These classes provide "evented" versions of mutable python containers.
They each have an `events` attribute (`SignalGroup`) that has a variety of
signals that will emit whenever the container is mutated.  See
[Container SignalGroups](#container-signalgroups) for the corresponding
container type for details on the available signals.
"""

from typing import TYPE_CHECKING, Any

from ._evented_dict import DictEvents, EventedDict
from ._evented_list import EventedList, ListEvents
from ._evented_set import EventedOrderedSet, EventedSet, OrderedSet, SetEvents
from ._selectable_evented_list import SelectableEventedList
from ._selection import Selection

if TYPE_CHECKING:
    from ._evented_proxy import (
        CallableProxyEvents,
        EventedCallableObjectProxy,
        EventedObjectProxy,
        ProxyEvents,
    )

__all__ = [
    "CallableProxyEvents",
    "DictEvents",
    "EventedCallableObjectProxy",
    "EventedDict",
    "EventedList",
    "EventedObjectProxy",
    "EventedOrderedSet",
    "EventedSet",
    "ListEvents",
    "OrderedSet",
    "ProxyEvents",
    "SelectableEventedList",
    "Selection",
    "SetEvents",
]


def __getattr__(name: str) -> Any:  # pragma: no cover
    if name == "EventedObjectProxy":
        from ._evented_proxy import EventedObjectProxy

        return EventedObjectProxy
    if name == "EventedCallableObjectProxy":
        from ._evented_proxy import EventedCallableObjectProxy

        return EventedCallableObjectProxy
    if name == "CallableProxyEvents":
        from ._evented_proxy import CallableProxyEvents

        return CallableProxyEvents
    if name == "ProxyEvents":
        from ._evented_proxy import ProxyEvents

        return ProxyEvents
    raise AttributeError(  # pragma: no cover
        f"module {__name__!r} has no attribute {name!r}"
    )
