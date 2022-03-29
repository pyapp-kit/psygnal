"""Dict that emits events when altered."""

from typing import (
    Any,
    Dict,
    Iterator,
    Mapping,
    MutableMapping,
    Sequence,
    Type,
    TypeVar,
    Union,
)

from .. import Signal, SignalGroup

_K = TypeVar("_K")
_T = TypeVar("_T")


class TypedMutableMapping(MutableMapping[_K, _T]):
    """Dictionary mixin that enforces item type."""

    def __init__(
        self,
        data: Mapping[_K, _T] = None,
        basetype: Union[Type[_T], Sequence[Type[_T]]] = (),
    ):
        if data is None:
            data = {}
        self._dict: Dict[_K, _T] = dict()
        self._basetypes = basetype if isinstance(basetype, Sequence) else (basetype,)
        self.update(data)

    def __setitem__(self, key: int, value: _T):  # noqa: F811
        self._dict[key] = self._type_check(value)

    def __delitem__(self, key: _K) -> None:
        del self._dict[key]

    def __getitem__(self, key: _K) -> _T:
        return self._dict[key]

    def __len__(self) -> int:
        return len(self._dict)

    def __iter__(self) -> Iterator[_T]:
        return iter(self._dict)

    def __repr__(self):
        return str(self._dict)

    def _type_check(self, e: Any) -> _T:
        if self._basetypes and not any(isinstance(e, t) for t in self._basetypes):
            raise TypeError(
                f"Cannot add object with type {type(e)} to TypedDict expecting type {self._basetypes}",
            )
        return e

    def __newlike__(self, iterable: MutableMapping[_K, _T]):
        new = self.__class__()
        # separating this allows subclasses to omit these from their `__init__`
        new._basetypes = self._basetypes
        new.update(**iterable)
        return new

    def copy(self) -> "TypedMutableMapping[_T]":
        """Return a shallow copy of the dictionary."""
        return self.__newlike__(self)


class DictEvents(SignalGroup):
    """Events available on EventedDict.

    Attributes
    ----------
    adding (key: _K)
        emitted before an item is added at `key`
    added (key: _K, value: _T)
        emitted after a `value` is added at `key`
    changing (key: _K, old_value: _T, value: _T)
        emitted before `old_value` is replaced with `value` at `key`
    changed (key: _K, old_value: _T, value: _T)
        emitted before `old_value` is replaced with `value` at `key`
    removing (key: _K)
        emitted before an item is removed at `key`
    removed (key: _K, value: _T)
        emitted after `value` is removed at `index`
    """

    adding = Signal(object)  # (key, )
    added = Signal(object, object)  # (key, value)
    changing = Signal(object)  # (key, )
    changed = Signal(object, object, object)  # (key, old_value, value)
    removing = Signal(object)  # (key, )
    removed = Signal(object, object)  # (key, value)


class EventedDict(TypedMutableMapping[_K, _T]):
    """Mutable dictionary that emits events when altered.
    This class is designed to behave exactly like the builtin `dict`, but
    will emit events before and after all mutations (addition, removal, and
    changing).

    Parameters
    ----------
    data : Mapping, optional
        Dictionary to initialize the class with.
    basetype : type of sequence of types, optional
        Type of the element in the dictionary.

    """

    events: DictEvents  # pragma: no cover

    def __init__(
        self,
        data: Mapping[_K, _T] = None,
        basetype: Union[Type[_T], Sequence[Type[_T]]] = (),
    ):
        self.events = DictEvents()
        super().__init__(data, basetype)

    def __setitem__(self, key: _K, value: _T):
        old_value = self._dict.get(key, None)
        if value is old_value or value == old_value:
            return
        if old_value is None:
            self.events.adding.emit(key)
            super().__setitem__(key, value)
            self.events.added.emit(key, value)
        else:
            self.events.changing.emit(key)
            super().__setitem__(key, value)
            self.events.changed.emit(key, old_value, value)

    def __delitem__(self, key: _K):
        self.events.removing.emit(key)
        item = self._dict.pop(key)
        self.events.removed.emit(key, item)