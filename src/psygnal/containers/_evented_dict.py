"""Dict that emits events when altered."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, MutableMapping, Sequence
from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar, TypeAlias, TypeVar, get_args

if TYPE_CHECKING:
    from pydantic import GetCoreSchemaHandler, SerializationInfo
    from typing_extensions import Self

from psygnal._group import EmissionInfo, PathStep, SignalGroup
from psygnal._signal import Signal, SignalInstance

_K = TypeVar("_K")
_V = TypeVar("_V")
TypeOrSequenceOfTypes: TypeAlias = type[_V] | Sequence[type[_V]]
DictArg: TypeAlias = Mapping[_K, _V] | Iterable[tuple[_K, _V]]


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
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> Mapping[str, Any]:
        """Return the Pydantic core schema for this object."""
        from pydantic_core import core_schema

        def _serialize(obj: EventedDict[_K, _V], info: SerializationInfo, /) -> Any:
            if info.mode_is_json():
                return obj._dict
            return cls(obj._dict)

        # get key/value types
        key_type = val_type = Any
        if args := get_args(source_type):
            key_type = args[0]
            if len(args) > 1:
                val_type = args[1]

        # get key/value schemas and validators
        keys_schema = handler.generate_schema(key_type)
        values_schema = handler.generate_schema(val_type)
        dict_schema = core_schema.dict_schema(
            keys_schema=keys_schema,
            values_schema=values_schema,
        )
        return core_schema.no_info_after_validator_function(
            function=cls,
            schema=dict_schema,
            json_schema_input_schema=dict_schema,
            serialization=core_schema.plain_serializer_function_ser_schema(
                _serialize,
                info_arg=True,
            ),
        )


class DictSignalInstance(SignalInstance):
    def _psygnal_relocate_info_(self, emission_info: EmissionInfo) -> EmissionInfo:
        """Relocate the emission info to the key being modified.

        (All signals on EventedDict have the key as the first argument.)
        """
        if args := emission_info.args:
            return emission_info.insert_path(PathStep(key=args[0]))
        return emission_info


DictSignal = partial(Signal, signal_instance_class=DictSignalInstance)


class DictEvents(SignalGroup):
    """Events available on [EventedDict][psygnal.containers.EventedDict]."""

    adding = DictSignal(object)  # (key, )
    """`(key,)` emitted before an item is added at `key`"""
    added = DictSignal(object, object)  # (key, value)
    """`(key, value)` emitted after a `value` is added at `key`"""
    changing = DictSignal(object)  # (key, )
    """`(key, old_value, new_value)` emitted before `old_value` is replaced with
    `new_value` at `key`"""
    changed = DictSignal(object, object, object)  # (key, old_value, value)
    """`(key, old_value, new_value)` emitted before `old_value` is replaced with
    `new_value` at `key`"""
    removing = DictSignal(object)  # (key, )
    """`(key,)` emitted before an item is removed at `key`"""
    removed = DictSignal(object, object)  # (key, value)
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
    _psygnal_group_: ClassVar[str] = "events"

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
