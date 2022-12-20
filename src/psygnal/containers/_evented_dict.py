"""Dict that emits events when altered."""

from typing import (
    Dict,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from .. import Signal, SignalGroup

_K = TypeVar("_K")
_V = TypeVar("_V")
TypeOrSequenceOfTypes = Union[Type[_V], Sequence[Type[_V]]]
DictArg = Union[Mapping[_K, _V], Iterable[Tuple[_K, _V]]]


class TypedMutableMapping(MutableMapping[_K, _V]):
    """Dictionary that enforces value type.

    Parameters
    ----------
    data : Union[Mapping[_K, _V], Iterable[Tuple[_K, _V]], None], optional
        Data suitable of passing to dict(). Mapping of {key: value} pairs, or
        Iterable of two-tuples [(key, value), ...], or None to create an
    basetype : TypeOrSequenceOfTypes, optional
        Type or Sequence of Type objects. If provided, values entered into this Mapping
        must be an instance of one of the provided types. by default ()
    """

    def __init__(
        self,
        data: Optional[DictArg] = None,
        *,
        basetype: TypeOrSequenceOfTypes = (),
        **kwargs: _V,
    ):

        self._dict: Dict[_K, _V] = {}
        self._basetypes: Tuple[Type[_V], ...] = (
            tuple(basetype) if isinstance(basetype, Sequence) else (basetype,)
        )
        self.update({} if data is None else data, **kwargs)

    def __setitem__(self, key: _K, value: _V) -> None:
        self._dict[key] = self._type_check(value)

    def __delitem__(self, key: _K) -> None:
        del self._dict[key]

    def __getitem__(self, key: _K) -> _V:
        return self._dict[key]

    def __len__(self) -> int:
        return len(self._dict)

    def __iter__(self) -> Iterator[_K]:
        return iter(self._dict)

    def __repr__(self) -> str:
        return repr(self._dict)

    def _type_check(self, value: _V) -> _V:
        """Check the types of items if basetypes are set for the model."""
        if self._basetypes and not any(isinstance(value, t) for t in self._basetypes):
            raise TypeError(
                f"Cannot add object with type {type(value)} to TypedDict expecting"
                f"type {self._basetypes}"
            )
        return value

    def __newlike__(
        self, mapping: MutableMapping[_K, _V]
    ) -> "TypedMutableMapping[_K, _V]":
        new = self.__class__()
        # separating this allows subclasses to omit these from their `__init__`
        new._basetypes = self._basetypes
        new.update(mapping)
        return new

    def copy(self) -> "TypedMutableMapping[_K, _V]":
        """Return a shallow copy of the dictionary."""
        return self.__newlike__(self)


class DictEvents(SignalGroup):
    """Events available on [EventedDict][psygnal.containers.EventedDict].

    Attributes
    ----------
    adding: Signal[Any]
        `(key,)` emitted before an item is added at `key`
    added : Signal[Any, Any]
        `(key, value)` emitted after a `value` is added at `key`
    changing : Signal[Any, Any, Any]
        `(key, old_value, new_value)` emitted before `old_value` is replaced with
        `new_value` at `key`
    changed : Signal[Any, Any, Any]
        `(key, old_value, new_value)` emitted before `old_value` is replaced with
        `new_value` at `key`
    removing: Signal[Any]
        `(key,)` emitted before an item is removed at `key`
    removed : Signal[Any, Any]
        `(key, value)` emitted after `value` is removed at `index`
    """

    adding = Signal(object)  # (key, )
    added = Signal(object, object)  # (key, value)
    changing = Signal(object)  # (key, )
    changed = Signal(object, object, object)  # (key, old_value, value)
    removing = Signal(object)  # (key, )
    removed = Signal(object, object)  # (key, value)


class EventedDict(TypedMutableMapping[_K, _V]):
    """Mutable mapping that emits events when altered.

    This class is designed to behave exactly like the builtin [`dict`][], but
    will emit events before and after all mutations (addition, removal, and
    changing).

    Parameters
    ----------
    data : Union[Mapping[_K, _V], Iterable[Tuple[_K, _V]], None], optional
        Data suitable of passing to dict(). Mapping of {key: value} pairs, or
        Iterable of two-tuples [(key, value), ...], or None to create an
    basetype : TypeOrSequenceOfTypes, optional
        Type or Sequence of Type objects. If provided, values entered into this Mapping
        must be an instance of one of the provided types. by default ().

    Attributes
    ----------
    events: DictEvents
        The `SignalGroup` object that emits all events available on an `EventedDict`.
    """

    events: DictEvents  # pragma: no cover

    def __init__(
        self,
        data: Optional[DictArg] = None,
        *,
        basetype: TypeOrSequenceOfTypes = (),
        **kwargs: _V,
    ):
        self.events = DictEvents()
        super().__init__(data, basetype=basetype, **kwargs)

    def __setitem__(self, key: _K, value: _V) -> None:
        if key not in self._dict:
            self.events.adding.emit(key)
            super().__setitem__(key, value)
            self.events.added.emit(key, value)
        else:
            old_value = self._dict[key]
            if value is not old_value:
                self.events.changing.emit(key)
                super().__setitem__(key, value)
                self.events.changed.emit(key, old_value, value)

    def __delitem__(self, key: _K) -> None:
        item = self._dict[key]
        self.events.removing.emit(key)
        super().__delitem__(key)
        self.events.removed.emit(key, item)

    def __repr__(self) -> str:
        return f"EventedDict({super().__repr__()})"
