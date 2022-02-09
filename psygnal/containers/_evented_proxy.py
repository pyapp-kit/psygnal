from functools import partial
from typing import Generic, TypeVar
from weakref import finalize

from wrapt import ObjectProxy

from .._group import SignalGroup
from .._signal import Signal

# we're using a cache instead of setting the events object directly on the proxy
# because when wrapt is compiled as a C extensions, the ObjectProxy is not allowed
# to add any new attributes.
_OBJ_CACHE = {}

T = TypeVar("T")
_UNSET = object()


class Events(SignalGroup):
    attribute_set = Signal(str, object)
    attribute_deleted = Signal(str)
    item_set = Signal(object, object)
    item_deleted = Signal(object)
    in_place = Signal(str, object)


class CallableEvents(Events):
    called = Signal(tuple, dict)


class _EventedObjectProxy(ObjectProxy, Generic[T]):
    @property
    def events(self) -> Events:
        obj_id = id(self)
        if obj_id not in _OBJ_CACHE:
            _OBJ_CACHE[obj_id] = Events()
            finalize(self, partial(_OBJ_CACHE.pop, obj_id, None))
        return _OBJ_CACHE[obj_id]

    def __setattr__(self, name, value):
        if hasattr(type(self), name):
            return object.__setattr__(self, name, value)

        before = getattr(self, name, _UNSET)
        super().__setattr__(name, value)
        after = getattr(self, name, _UNSET)
        if before is not after:
            self.events.attribute_set(name, after)

    def __delattr__(self, name):
        super().__delattr__(name)
        self.events.attribute_deleted(name)

    def __setitem__(self, key, value):
        before = self[key]
        super().__setitem__(key, value)
        after = self[key]
        if before is not after:
            self.events.item_set(key, after)

    def __delitem__(self, key):
        super().__delitem__(key)
        self.events.item_deleted(key)

    def __repr__(self) -> str:
        return repr(self.__wrapped__)

    def __dir__(self):
        return dir(self.__wrapped__) + ["events"]

    def __getattr__(self, name):
        if hasattr(type(self), name):
            return object.__getattribute__(self, name)

        return super().__getattr__(name)

    def __iadd__(self, other):
        self.events.in_place("add", other)
        return super().__iadd__(other)

    def __isub__(self, other):
        self.events.in_place("sub", other)
        return super().__isub__(other)

    def __imul__(self, other):
        self.events.in_place("mul", other)
        return super().__imul__(other)

    def __idiv__(self, other):
        self.events.in_place("div", other)
        return super().__idiv__(other)

    def __itruediv__(self, other):
        self.events.in_place("truediv", other)
        return super().__itruediv__(other)

    def __ifloordiv__(self, other):
        self.events.in_place("floordiv", other)
        return super().__ifloordiv__(other)

    def __imod__(self, other):
        self.events.in_place("mod", other)
        return super().__imod__(other)

    def __ipow__(self, other):
        self.events.in_place("pow", other)
        return super().__ipow__(other)

    def __ilshift__(self, other):
        self.events.in_place("lshift", other)
        return super().__ilshift__(other)

    def __irshift__(self, other):
        self.events.in_place("rshift", other)
        return super().__irshift__(other)

    def __iand__(self, other):
        self.events.in_place("and", other)
        return super().__iand__(other)

    def __ixor__(self, other):
        self.events.in_place("xor", other)
        return super().__ixor__(other)

    def __ior__(self, other):
        self.events.in_place("or", other)
        return super().__ior__(other)


class _EventedCallableObjectProxy(_EventedObjectProxy):
    @property
    def events(self) -> Events:
        obj_id = id(self)
        if obj_id not in _OBJ_CACHE:
            _OBJ_CACHE[obj_id] = CallableEvents()
            finalize(self, partial(_OBJ_CACHE.pop, obj_id, None))
        return _OBJ_CACHE[obj_id]

    def __call__(self, *args, **kwargs):
        self.events.called(args, kwargs)
        return self.__wrapped__(*args, **kwargs)


def EventedObjectProxy(target: T) -> T:
    return _EventedObjectProxy(target)
