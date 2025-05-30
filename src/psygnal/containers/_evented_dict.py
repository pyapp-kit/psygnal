"""Dict that emits events when altered."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, MutableMapping, Sequence
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    TypeVar,
    Union,
    get_args,
)

if TYPE_CHECKING:
    from typing_extensions import Self

from psygnal._group import SignalGroup
from psygnal._signal import Signal

_K = TypeVar("_K")
_V = TypeVar("_V")
TypeOrSequenceOfTypes = Union[type[_V], Sequence[type[_V]]]
DictArg = Union[Mapping[_K, _V], Iterable[tuple[_K, _V]]]


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
        data: DictArg | None = None,
        *,
        basetype: TypeOrSequenceOfTypes = (),
        **kwargs: _V,
    ):
        self._dict: dict[_K, _V] = {}
        self._basetypes: tuple[type[_V], ...] = (
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

    def __newlike__(self, mapping: MutableMapping[_K, _V]) -> Self:
        new = self.__class__()
        # separating this allows subclasses to omit these from their `__init__`
        new._basetypes = self._basetypes
        new.update(mapping)
        return new

    def copy(self) -> Self:
        """Return a shallow copy of the dictionary."""
        return self.__newlike__(self)

    def __copy__(self) -> Self:
        return self.copy()

    # PYDANTIC SUPPORT

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: Callable
    ) -> Mapping[str, Any]:
        """Return the Pydantic core schema for this object."""
        from pydantic_core import core_schema

        args = get_args(source_type)
        return core_schema.no_info_after_validator_function(
            function=cls,
            schema=core_schema.dict_schema(
                keys_schema=handler(args[0]) if args else None,
                values_schema=handler(args[1]) if len(args) > 1 else None,
            ),
        )


class DictEvents(SignalGroup):
    """Events available on [EventedDict][psygnal.containers.EventedDict]."""

    adding = Signal(object)  # (key, )
    """`(key,)` emitted before an item is added at `key`"""
    added = Signal(object, object)  # (key, value)
    """`(key, value)` emitted after a `value` is added at `key`"""
    changing = Signal(object)  # (key, )
    """`(key, old_value, new_value)` emitted before `old_value` is replaced with
    `new_value` at `key`"""
    changed = Signal(object, object, object)  # (key, old_value, value)
    """`(key, old_value, new_value)` emitted before `old_value` is replaced with
    `new_value` at `key`"""
    removing = Signal(object)  # (key, )
    """`(key,)` emitted before an item is removed at `key`"""
    removed = Signal(object, object)  # (key, value)
    """`(key, value)` emitted after `value` is removed at `key`"""


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
        data: DictArg | None = None,
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
        return f"{self.__class__.__name__}({super().__repr__()})"
