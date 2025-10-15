"""MutableSequence that emits events when altered.

Note For Developers
===================

Be cautious when re-implementing typical list-like methods here (e.g. extend,
pop, clear, etc...).  By not re-implementing those methods, we force ALL "CRUD"
(create, read, update, delete) operations to go through a few key methods
defined by the abc.MutableSequence interface, where we can emit the necessary
events.

Specifically:

- `insert` = "create" : add a new item/index to the list
- `__getitem__` = "read" : get the value of an existing index
- `__setitem__` = "update" : update the value of an existing index
- `__delitem__` = "delete" : remove an existing index from the list

All of the additional list-like methods are provided by the MutableSequence
interface, and call one of those 4 methods.  So if you override a method, you
MUST make sure that all the appropriate events are emitted.  (Tests should
cover this in test_evented_list.py)
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableSequence
from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    TypeAlias,
    TypeVar,
    cast,
    get_args,
    overload,
)

from psygnal._group import EmissionInfo, PathStep, SignalGroup
from psygnal._signal import Signal, SignalInstance
from psygnal.utils import iter_signal_instances

if TYPE_CHECKING:
    from pydantic import GetCoreSchemaHandler, SerializationInfo
    from typing_extensions import Self

_T = TypeVar("_T")
Index: TypeAlias = int | slice


class ListSignalInstance(SignalInstance):
    def _psygnal_relocate_info_(self, emission_info: EmissionInfo) -> EmissionInfo:
        """Relocate the emission info to the index being modified.

        (All signals on EventedList have the index as the first argument.)
        """
        if args := emission_info.args:
            return emission_info.insert_path(PathStep(index=args[0]))
        return emission_info


ListSignal = partial(Signal, signal_instance_class=ListSignalInstance)


class ListEvents(SignalGroup):
    """Events available on [EventedList][psygnal.containers.EventedList]."""

    inserting = ListSignal(int)
    """`(index)` emitted before an item is inserted at `index`"""
    inserted = ListSignal(int, object)
    """`(index, value)` emitted after `value` is inserted at `index`"""
    removing = ListSignal(int)
    """`(index)` emitted before an item is removed at `index`"""
    removed = ListSignal(int, object)
    """`(index, value)` emitted after `value` is removed at `index`"""
    moving = ListSignal(int, int)
    """`(index, new_index)` emitted before an item is moved from `index` to
    `new_index`"""
    moved = ListSignal(int, int, object)
    """`(index, new_index, value)` emitted after `value` is moved from
    `index` to `new_index`"""
    changed = ListSignal(object, object, object)
    """`(index_or_slice, old_value, value)` emitted when `index` is set from
    `old_value` to `value`"""
    reordered = Signal()
    """Emitted when the list is reordered (eg. moved/reversed)."""
    child_event = Signal(EmissionInfo)
    """`(EmissionInfo)` emitted when an object in the list emits an
    event. Note that the `EventedList` must be created with `child_events=True` in
    order for this to be emitted.
    """


class EventedList(MutableSequence[_T]):
    """Mutable Sequence that emits events when altered.

    This class is designed to behave exactly like the builtin `list`, but
    will emit events before and after all mutations (insertion, removal,
    setting, and moving).

    Parameters
    ----------
    data : iterable, optional
        Elements to initialize the list with.
    hashable : bool
        Whether the list should be hashable as id(self). By default `True`.
    child_events: bool
        Whether to re-emit events from emitted from evented items in the list
        (i.e. items that have SignalInstances). If `True`, child events can be connected
        at `EventedList.events.child_event`. By default, `True`.

    Attributes
    ----------
    events : ListEvents
        SignalGroup that with events related to list mutation.  (see ListEvents)
    """

    events: ListEvents  # pragma: no cover
    _psygnal_group_: ClassVar[str] = "events"

    def __init__(
        self,
        data: Iterable[_T] = (),
        *,
        hashable: bool = True,
        child_events: bool = True,
    ):
        super().__init__()
        self._data: list[_T] = []
        self._hashable = hashable
        self._child_events = child_events
        self.events = ListEvents(instance=self)
        self.extend(data)

    # WAIT!! ... Read the module docstring before reimplement these methods
    # def append(self, item): ...
    # def clear(self): ...
    # def pop(self, index=-1): ...
    # def extend(self, value: Iterable[_T]): ...
    # def remove(self, value: Any): ...

    def insert(self, index: int, value: _T) -> None:
        """Insert `value` before index."""
        _value = self._pre_insert(value)
        self.events.inserting.emit(index)
        self._data.insert(index, _value)
        self.events.inserted.emit(index, value)
        self._post_insert(value)

    @overload
    def __getitem__(self, key: int) -> _T: ...

    @overload
    def __getitem__(self, key: slice) -> Self: ...

    def __getitem__(self, key: Index) -> _T | Self:
        """Return self[key]."""
        result = self._data[key]
        return self.__newlike__(result) if isinstance(result, list) else result

    @overload
    def __setitem__(self, key: int, value: _T) -> None: ...

    @overload
    def __setitem__(self, key: slice, value: Iterable[_T]) -> None: ...

    def __setitem__(self, key: Index, value: _T | Iterable[_T]) -> None:
        """Set self[key] to value."""
        old = self._data[key]
        if value is old:
            return

        # sourcery skip: hoist-similar-statement-from-if, hoist-statement-from-if
        if isinstance(key, slice):
            if not isinstance(value, Iterable):
                raise TypeError("Can only assign an iterable to slice")
            value = [self._pre_insert(v) for v in value]  # before we mutate the list
            self._data[key] = value
        else:
            value = self._pre_insert(cast("_T", value))
            self._data[key] = value

        self.events.changed.emit(key, old, value)

    def __delitem__(self, key: Index) -> None:
        """Delete self[key]."""
        # delete from the end
        for parent, index in sorted(self._delitem_indices(key), reverse=True):
            parent.events.removing.emit(index)
            parent._pre_remove(index)
            item = parent._data.pop(index)
            self.events.removed.emit(index, item)

    def _delitem_indices(self, key: Index) -> Iterable[tuple[EventedList[_T], int]]:
        # returning (self, int) allows subclasses to pass nested members
        if isinstance(key, int):
            yield (self, key if key >= 0 else key + len(self))
        elif isinstance(key, slice):
            yield from ((self, i) for i in range(*key.indices(len(self))))
        else:
            n = repr(type(key).__name__)
            raise TypeError(f"EventedList indices must be integers or slices, not {n}")

    def _pre_insert(self, value: _T) -> _T:
        """Validate and or modify values prior to inserted."""
        return value

    def _post_insert(self, new_item: _T) -> None:
        """Modify and or handle values after insertion."""
        if self._child_events:
            self._connect_child_emitters(new_item)

    def _pre_remove(self, index: int) -> None:
        """Modify and or handle values before removal."""
        if self._child_events:
            self._disconnect_child_emitters(self[index])

    def __newlike__(self, iterable: Iterable[_T]) -> Self:
        """Return new instance of same class."""
        return self.__class__(iterable)

    def copy(self) -> Self:
        """Return a shallow copy of the list."""
        return self.__newlike__(self)

    def __copy__(self) -> Self:
        return self.copy()

    def __add__(self, other: Iterable[_T]) -> Self:
        """Add other to self, return new object."""
        copy = self.copy()
        copy.extend(other)
        return copy

    def __iadd__(self, other: Iterable[_T]) -> Self:
        """Add other to self in place (self += other)."""
        self.extend(other)
        return self

    def __radd__(self, other: list) -> list:
        """Reflected add (other + self).  Cast self to list."""
        return other + list(self)

    def __len__(self) -> int:
        """Return len(self)."""
        return len(self._data)

    def __repr__(self) -> str:
        """Return repr(self)."""
        return f"{type(self).__name__}({self._data})"

    def __eq__(self, other: Any) -> bool:
        """Return self==value."""
        return bool(self._data == other)

    def __hash__(self) -> int:
        """Return hash(self)."""
        # it's important to add this to allow this object to be hashable
        # given that we've also reimplemented __eq__
        if self._hashable:
            return id(self)
        name = self.__class__.__name__
        raise TypeError(
            f"unhashable type: {name!r}. "
            f"Create with {name}(..., hashable=True) if you need hashability"
        )

    def reverse(self, *, emit_individual_events: bool = False) -> None:
        """Reverse list *IN PLACE*."""
        if emit_individual_events:
            super().reverse()
        else:
            self._data.reverse()
        self.events.reordered.emit()

    def move(self, src_index: int, dest_index: int = 0) -> bool:
        """Insert object at `src_index` before `dest_index`.

        Both indices refer to the list prior to any object removal
        (pre-move space).
        """
        if dest_index < 0:
            dest_index += len(self) + 1
        if dest_index in (src_index, src_index + 1):
            # this is a no-op
            return False

        self.events.moving.emit(src_index, dest_index)
        item = self._data.pop(src_index)
        if dest_index > src_index:
            dest_index -= 1
        self._data.insert(dest_index, item)
        self.events.moved.emit(src_index, dest_index, item)
        self.events.reordered.emit()
        return True

    def move_multiple(self, sources: Iterable[Index], dest_index: int = 0) -> int:
        """Move a batch of `sources` indices, to a single destination.

        Note, if `dest_index` is higher than any of the `sources`, then
        the resulting position of the moved objects after the move operation
        is complete will be lower than `dest_index`.

        Parameters
        ----------
        sources : Iterable[Union[int, slice]]
            A sequence of indices
        dest_index : int, optional
            The destination index.  All sources will be inserted before this
            index (in pre-move space), by default 0... which has the effect of
            "bringing to front" everything in `sources`, or acting as a
            "reorder" method if `sources` contains all indices.

        Returns
        -------
        int
            The number of successful move operations completed.

        Raises
        ------
        TypeError
            If the destination index is a slice, or any of the source indices
            are not `int` or `slice`.
        """
        # calling list here makes sure that there are no index errors up front
        move_plan = list(self._move_plan(sources, dest_index))

        # don't assume index adjacency ... so move objects one at a time
        # this *could* be simplified with an intermediate list ... but this way
        # allows any views (such as QtViews) to update themselves more easily.
        # If this needs to be changed in the future for performance reasons,
        # then the associated QtListView will need to changed from using
        # `beginMoveRows` & `endMoveRows` to using `layoutAboutToBeChanged` &
        # `layoutChanged` while *manually* updating model indices with
        # `changePersistentIndexList`.  That becomes much harder to do with
        # nested tree-like models.
        with self.events.reordered.blocked():
            for src, dest in move_plan:
                self.move(src, dest)

        self.events.reordered.emit()
        return len(move_plan)

    def _move_plan(
        self, sources: Iterable[Index], dest_index: int
    ) -> Iterable[tuple[int, int]]:
        """Yield prepared indices for a multi-move.

        Given a set of `sources` from anywhere in the list,
        and a single `dest_index`, this function computes and yields
        `(from_index, to_index)` tuples that can be used sequentially in
        single move operations.  It keeps track of what has moved where and
        updates the source and destination indices to reflect the model at each
        point in the process.

        This is useful for a drag-drop operation with a QtModel/View.

        Parameters
        ----------
        sources : Iterable[tuple[int, ...]]
            An iterable of tuple[int] that should be moved to `dest_index`.
        dest_index : Tuple[int]
            The destination for sources.
        """
        if isinstance(dest_index, slice):
            raise TypeError("Destination index may not be a slice")  # pragma: no cover

        to_move: list[int] = []
        for idx in sources:
            if isinstance(idx, slice):
                to_move.extend(list(range(*idx.indices(len(self)))))
            elif isinstance(idx, int):
                to_move.append(idx)
            else:
                raise TypeError(
                    "Can only move integer or slice indices"
                )  # pragma: no cover

        to_move = list(dict.fromkeys(to_move))

        if dest_index < 0:
            dest_index += len(self) + 1

        d_inc = 0
        popped: list[int] = []
        for i, src in enumerate(to_move):
            if src != dest_index:
                # we need to decrement the src_i by 1 for each time we have
                # previously pulled items out from in front of the src_i
                src -= sum(x <= src for x in popped)
                # if source is past the insertion point, increment src for each
                # previous insertion
                if src >= dest_index:
                    src += i
                yield src, dest_index + d_inc

            popped.append(src)
            # if the item moved up, increment the destination index
            if dest_index <= src:
                d_inc += 1

    def _connect_child_emitters(self, child: _T) -> None:
        """Connect all events from the child to be reemitted."""
        for emitter in iter_signal_instances(child):
            emitter.connect(self._reemit_child_event)

    def _disconnect_child_emitters(self, child: _T) -> None:
        """Disconnect all events from the child from the reemitter."""
        for emitter in iter_signal_instances(child):
            emitter.disconnect(self._reemit_child_event)

    def _reemit_child_event(self, *args: Any) -> None:
        """Re-emit event from child with index."""
        emitter = Signal.current_emitter()
        if emitter is None:
            return  # pragma: no cover
        obj = emitter.instance
        try:
            idx = self.index(obj)
        except ValueError:  # pragma: no cover
            return

        if args and isinstance(args[0], EmissionInfo):
            child_info = EmissionInfo(
                signal=args[0].signal,
                args=args[0].args,
                path=(PathStep(index=idx), *args[0].path),
            )
        else:
            child_info = EmissionInfo(
                signal=emitter,
                args=args,
                path=(PathStep(index=idx), PathStep(attr=emitter.name)),
            )

        self.events.child_event.emit(child_info)

    # PYDANTIC SUPPORT

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> Mapping[str, Any]:
        """Return the Pydantic core schema for this object."""
        from pydantic_core import core_schema

        def _serialize(obj: EventedList[_T], info: SerializationInfo, /) -> Any:
            if info.mode_is_json():
                return obj._data
            return cls(obj._data)

        item_type = args[0] if (args := get_args(source_type)) else Any
        items_schema = handler.generate_schema(item_type)
        list_schema = core_schema.list_schema(items_schema=items_schema)
        return core_schema.no_info_after_validator_function(
            function=cls,
            schema=list_schema,
            json_schema_input_schema=list_schema,
            serialization=core_schema.plain_serializer_function_ser_schema(
                _serialize,
                info_arg=True,
            ),
        )
