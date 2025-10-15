from collections.abc import Callable
from functools import partial
from typing import Any, ClassVar, Generic, TypeVar
from weakref import finalize

try:
    from wrapt import ObjectProxy
except ImportError as e:
    raise type(e)(
        f"{e}. Please `pip install psygnal[proxy]` to use EventedObjectProxies"
    ) from e

from psygnal._group import SignalGroup
from psygnal._signal import Signal

T = TypeVar("T")
_UNSET = object()


class ProxyEvents(SignalGroup):
    """Events emitted by `EventedObjectProxy` and `EventedCallableObjectProxy`."""

    attribute_set = Signal(str, object)
    """Emitted when an attribute is set."""
    attribute_deleted = Signal(str)
    """Emitted when an attribute is deleted."""
    item_set = Signal(object, object)
    """Emitted when an item is set."""
    item_deleted = Signal(object)
    """Emitted when an item is deleted."""
    in_place = Signal(str, object)
    """Emitted when an in-place operation is performed."""


class CallableProxyEvents(ProxyEvents):
    """Events emitted by `EventedCallableObjectProxy`."""

    called = Signal(tuple, dict)
    """Emitted when the object is called."""


# we're using a cache instead of setting the events object directly on the proxy
# because when wrapt is compiled as a C extensions, the ObjectProxy is not allowed
# to add any new attributes.
_OBJ_CACHE: dict[int, ProxyEvents] = {}


class EventedObjectProxy(ObjectProxy, Generic[T]):
    """Create a proxy of `target` that includes an `events` [psygnal.SignalGroup][].

    Provides an "evented" subclasses of
    [`wrapt.ObjectProxy`](https://wrapt.readthedocs.io/en/latest/wrappers.html#object-proxy)

    !!! important

        This class requires `wrapt` to be installed.
        You can install directly (`pip install wrapt`) or by using the psygnal
        extra: `pip install psygnal[proxy]`

    Signals will be emitted whenever an attribute is set or deleted, or
    (if the object implements `__getitem__`) whenever an item is set or deleted.
    If the object supports in-place modification (i.e. any of the `__i{}__` magic
    methods), then an `in_place` event is emitted (with the name of the method)
    whenever any of them are used.

    The events available at target.events include:

    - `attribute_set`: `Signal(str, object)`
    - `attribute_deleted`: `Signal(str)`
    - `item_set`: `Signal(object, object)`
    - `item_deleted`: `Signal(object)`
    - `in_place`: `Signal(str, object)`

    !!! warning "Experimental"

        This object is experimental! They may affect the behavior of
        the wrapped object in unanticipated ways.  Please consult
        the [wrapt documentation](https://wrapt.readthedocs.io/en/latest/wrappers.html)
        for details on how the Object Proxy works.

    Parameters
    ----------
    target : Any
        An object to wrap
    """

    _psygnal_group_: ClassVar[str] = "events"

    def __init__(self, target: Any):
        super().__init__(target)

    @property
    def events(self) -> ProxyEvents:  # pragma: no cover # unclear why
        """`SignalGroup` containing events for this object proxy."""
        obj_id = id(self)
        if obj_id not in _OBJ_CACHE:
            _OBJ_CACHE[obj_id] = ProxyEvents()
            finalize(self, partial(_OBJ_CACHE.pop, obj_id, None))
        return _OBJ_CACHE[obj_id]

    def __setattr__(self, name: str, value: None) -> None:
        before = getattr(self, name, _UNSET)
        super().__setattr__(name, value)
        if before is not (after := getattr(self, name, _UNSET)):
            self.events.attribute_set(name, after)

    def __delattr__(self, name: str) -> None:
        super().__delattr__(name)
        self.events.attribute_deleted(name)

    def __setitem__(self, key: Any, value: Any) -> None:
        before = self[key]
        super().__setitem__(key, value)
        if before is not (after := self[key]):
            self.events.item_set(key, after)

    def __delitem__(self, key: Any) -> None:
        super().__delitem__(key)
        self.events.item_deleted(key)

    def __repr__(self) -> str:
        return repr(self.__wrapped__)

    def __dir__(self) -> list[str]:
        return [*dir(self.__wrapped__), "events"]

    def __iadd__(self, other: Any) -> T:
        self.events.in_place("add", other)
        return super().__iadd__(other)  # type: ignore

    def __isub__(self, other: Any) -> T:
        self.events.in_place("sub", other)
        return super().__isub__(other)  # type: ignore

    def __imul__(self, other: Any) -> T:
        self.events.in_place("mul", other)
        return super().__imul__(other)  # type: ignore

    def __imatmul__(self, other: Any) -> T:
        self.events.in_place("matmul", other)
        self.__wrapped__ @= other  # not in wrapt  # type: ignore
        return self

    def __itruediv__(self, other: Any) -> T:
        self.events.in_place("truediv", other)
        return super().__itruediv__(other)  # type: ignore

    def __ifloordiv__(self, other: Any) -> T:
        self.events.in_place("floordiv", other)
        return super().__ifloordiv__(other)  # type: ignore

    def __imod__(self, other: Any) -> T:
        self.events.in_place("mod", other)
        return super().__imod__(other)  # type: ignore

    def __ipow__(self, other: Any) -> T:
        self.events.in_place("pow", other)
        return super().__ipow__(other)  # type: ignore

    def __ilshift__(self, other: Any) -> T:
        self.events.in_place("lshift", other)
        return super().__ilshift__(other)  # type: ignore

    def __irshift__(self, other: Any) -> T:
        self.events.in_place("rshift", other)
        return super().__irshift__(other)  # type: ignore

    def __iand__(self, other: Any) -> T:
        self.events.in_place("and", other)
        return super().__iand__(other)  # type: ignore

    def __ixor__(self, other: Any) -> T:
        self.events.in_place("xor", other)
        return super().__ixor__(other)  # type: ignore

    def __ior__(self, other: Any) -> T:
        self.events.in_place("or", other)
        return super().__ior__(other)  # type: ignore


class EventedCallableObjectProxy(EventedObjectProxy):
    """Create a proxy of `target` that includes an `events` [psygnal.SignalGroup][].

    `target` must be callable.

    !!! important

        This class requires `wrapt` to be installed.
        You can install directly (`pip install wrapt`) or by using the psygnal
        extra: `pip install psygnal[proxy]`

    Signals will be emitted whenever an attribute is set or deleted, or
    (if the object implements `__getitem__`) whenever an item is set or deleted.
    If the object supports in-place modification (i.e. any of the `__i{}__` magic
    methods), then an `in_place` event is emitted (with the name of the method)
    whenever any of them are used.  Lastly, if the item is called, a `called`
    event is emitted with the (args, kwargs) used in the call.

    The events available at `target.events` include:

    - `attribute_set`: `Signal(str, object)`
    - `attribute_deleted`: `Signal(str)`
    - `item_set`: `Signal(object, object)`
    - `item_deleted`: `Signal(object)`
    - `in_place`: `Signal(str, object)`
    - `called`: `Signal(tuple, dict)`

    Parameters
    ----------
    target : Callable
        An callable object to wrap

    """

    def __init__(self, target: Callable):
        super().__init__(target)

    @property
    def events(self) -> CallableProxyEvents:  # pragma: no cover # unclear why
        """`SignalGroup` containing events for this object proxy."""
        obj_id = id(self)
        if obj_id not in _OBJ_CACHE:
            _OBJ_CACHE[obj_id] = CallableProxyEvents()
            finalize(self, partial(_OBJ_CACHE.pop, obj_id, None))
        return _OBJ_CACHE[obj_id]  # type: ignore

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Call the wrapped object and emit a `called` signal."""
        self.events.called(args, kwargs)
        return self.__wrapped__(*args, **kwargs)
