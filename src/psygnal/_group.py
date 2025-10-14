"""A SignalGroup class that allows connecting to all SignalInstances on the class.

Note that unlike a slot/callback connected to SignalInstance.connect, a slot connected
to SignalGroup.connect does *not* receive the direct arguments that were emitted by a
given SignalInstance. Instead, the slot/callback will receive an EmissionInfo named
tuple, which contains `.signal`: the SignalInstance doing the emitting, and `.args`:
the args that were emitted.

"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Literal,
    SupportsIndex,
    overload,
)

from psygnal._signal import _NULL, Signal, SignalInstance, _SignalBlocker

from ._mypyc import mypyc_attr

if TYPE_CHECKING:
    import threading
    from collections.abc import (
        Callable,
        Container,
        Hashable,
        Iterable,
        Iterator,
        Mapping,
    )
    from contextlib import AbstractContextManager

    from psygnal._signal import F, ReducerFunc
    from psygnal._weak_callback import RefErrorChoice, WeakCallback

__all__ = ["EmissionInfo", "SignalGroup"]


@dataclass(slots=True, frozen=True)
class PathStep:
    """A single step in a path to a nested signal.

    This is used to represent a path to a signal that is nested inside an object,
    such as when a signal is emitted from a nested object or a list.  The
    `EmissionInfo.path` is a tuple of `PathStep` objects, where each `PathStep`
    represents either:

    - an _attribute_ access (e.g. `.foo`)
    - an _index_ access (e.g. `[3]`)
    - a _key_ access (e.g. `['user']`)

    !!! note
        _yes, `index` and `key` both just get passed to `__getitem__` in the end, but we
        differentiate them here to make it clearer whether the step is a key in a
        `Mapping` or an index in a `Sequence`._
    """

    attr: str | None = None
    index: SupportsIndex | None = None
    key: Hashable | None = None

    def __post_init__(self) -> None:
        # enforce mutual exclusivity
        if sum(x is not None for x in (self.attr, self.index, self.key)) != 1:
            raise ValueError(
                "PathStep must have exactly one of attr, index, or key set."
            )

    # nice debug display: .foo, [3], ['user']
    def __repr__(self) -> str:  # pragma: no cover
        if self.attr is not None:
            return f".{self.attr}"

        if self.index is not None:
            return f"[{int(self.index)}]"

        key = repr(self.key)
        if len(key) > 20 and not isinstance(self.key, str):
            key = f"{key[:17]}..."
        return f"[{key}]"


@dataclass(slots=True, frozen=True)
class EmissionInfo:
    """Tuple containing information about an emission event.

    Attributes
    ----------
    signal : SignalInstance
        The SignalInstance doing the emitting
    args: tuple
        The args that were emitted
    path: tuple[PathStep, ...]
        A tuple of PathStep objects that describe the path to the signal that was
        emitted. This is useful for nested signals, where the path can be used to
        determine the hierarchy of the signals.  For example, if a signal is emitted
        from a nested object like `bar.foo[3]['user']`, the path will contain the steps
        to get to that object, such as (PathStep(attr='foo'), PathStep(index=3),
        PathStep(key='user')).
    """

    signal: SignalInstance
    args: tuple[Any, ...]
    path: tuple[PathStep, ...] = ()

    def insert_path(self, *path: PathStep) -> EmissionInfo:
        """Return a new EmissionInfo with the given path steps inserted at the front."""
        return EmissionInfo(self.signal, self.args, (*path, *self.path))

    def __post_init__(self) -> None:
        if self.path and not all(
            isinstance(p, (PathStep, str, int)) for p in self.path
        ):
            raise TypeError(
                "EmissionInfo.path must be a tuple of PathStep objects, "
                "or a tuple of str or int."
            )

    def __iter__(self) -> Iterator[Any]:  # pragma: no cover
        """Iterate over the EmissionInfo and all nested EmissionInfos."""
        warnings.warn(
            "`EmissionInfo.__iter__` is no longer a NamedTuple and should not be "
            "iterated over.  Use direct attribute access instead.",
            RuntimeWarning,
            stacklevel=2,
        )
        yield self.signal
        yield self.args


class SignalRelay(SignalInstance):
    """Special SignalInstance that can be used to connect to all signals in a group.

    This class will rarely be instantiated by a user (or anything other than a
    SignalGroup).

    Parameters
    ----------
    signals : Mapping[str, SignalInstance]
        A mapping of signal names to SignalInstance instances.
    instance : Any, optional
        An object to which this `SignalRelay` is bound, by default None
    """

    def __init__(
        self, signals: Mapping[str, SignalInstance], instance: Any = None
    ) -> None:
        super().__init__(signature=(EmissionInfo,), instance=instance)
        self._signals = MappingProxyType(signals)
        self._sig_was_blocked: dict[str, bool] = {}
        self._on_first_connect_callbacks: list[Callable[[], None]] = []

    def _append_slot(self, slot: WeakCallback) -> None:
        super()._append_slot(slot)
        if len(self._slots) == 1:
            self._connect_relay()

    def _connect_relay(self) -> None:
        # Call any registered callbacks on first connection
        for callback in self._on_first_connect_callbacks:
            callback()

        # silence any warnings about failed weakrefs (will occur in compiled version)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for sig in self._signals.values():
                sig.connect(
                    self._slot_relay, check_nargs=False, check_types=False, unique=True
                )

    def _remove_slot(self, slot: int | WeakCallback | Literal["all"]) -> None:
        super()._remove_slot(slot)
        if not self._slots:
            self._disconnect_relay()

    def _disconnect_relay(self) -> None:
        for sig in self._signals.values():
            sig.disconnect(self._slot_relay)

    def _slot_relay(self, *args: Any, loc: PathStep | None = None) -> None:
        """Relay signals from child to parent.

        This is an important method for SignalGroups.  It is the method that is
        responsible for relaying signals from all child signals within the group
        to any connected slots on the group itself.
        """
        emitter = Signal.current_emitter()
        if emitter is None:
            return

        par_path = (loc,) if loc is not None else ()
        # If child already gave us an EmissionInfo, use it;
        if args and isinstance((info := args[0]), EmissionInfo):
            child_info = info.insert_path(*par_path)
        # else wrap its args unchanged
        else:
            child_info = emitter._psygnal_relocate_info_(
                EmissionInfo(signal=emitter, args=args, path=par_path)
            )

        self._run_emit_loop((child_info,))

    def _relay_partial(self, loc: PathStep | None) -> _relay_partial:
        """Return special partial that will call _slot_relay with 'loc'."""
        return _relay_partial(self, loc)

    def connect_direct(
        self,
        slot: Callable | None = None,
        *,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | Literal["raise"] = False,
        max_args: int | None = None,
    ) -> Callable[[Callable], Callable] | Callable:
        """Connect `slot` to be called whenever *any* Signal in this group is emitted.

        Params are the same as `psygnal.SignalInstance.connect`.  It's probably
        best to check whether all signals are uniform (i.e. have the same signature).

        Parameters
        ----------
        slot : Callable
            A callable to connect to this signal.  If the callable accepts less
            arguments than the signature of this slot, then they will be discarded when
            calling the slot.
        check_nargs : bool | None
            If `True` and the provided `slot` requires more positional arguments than
            the signature of this Signal, raise `TypeError`. by default `True`.
        check_types : bool | None
            If `True`, An additional check will be performed to make sure that types
            declared in the slot signature are compatible with the signature
            declared by this signal, by default `False`.
        unique : bool | Literal["raise"]
            If `True`, returns without connecting if the slot has already been
            connected.  If the literal string "raise" is passed to `unique`, then a
            `ValueError` will be raised if the slot is already connected.
            By default `False`.
        max_args : int, optional
            If provided, `slot` will be called with no more more than `max_args` when
            this SignalInstance is emitted.  (regardless of how many arguments are
            emitted).

        Returns
        -------
        Union[Callable[[Callable], Callable], Callable]
            [description]
        """

        def _inner(slot: Callable) -> Callable:
            for sig in self._signals.values():
                sig.connect(
                    slot,
                    check_nargs=check_nargs,
                    check_types=check_types,
                    unique=unique,
                    max_args=max_args,
                )
            return slot

        return _inner if slot is None else _inner(slot)

    def block(self, exclude: Container[str | SignalInstance] = ()) -> None:
        """Block this signal and all emitters from emitting."""
        super().block()
        for name, sig in self._signals.items():
            if name in exclude or sig in exclude:
                continue
            self._sig_was_blocked[name] = sig._is_blocked
            sig.block()

    def unblock(self) -> None:
        """Unblock this signal and all emitters, allowing them to emit."""
        super().unblock()
        for name, sig in self._signals.items():
            if not self._sig_was_blocked.pop(name, False):
                sig.unblock()

    def blocked(
        self, exclude: Container[str | SignalInstance] = ()
    ) -> AbstractContextManager[None]:
        """Context manager to temporarily block all emitters in this group.

        Parameters
        ----------
        exclude : iterable of str or SignalInstance, optional
            An iterable of signal instances or names to exempt from the block,
            by default ()
        """
        return _SignalBlocker(self, exclude=exclude)

    def disconnect(self, slot: Callable | None = None, missing_ok: bool = True) -> None:
        """Disconnect slot from all signals.

        Parameters
        ----------
        slot : callable, optional
            The specific slot to disconnect.  If `None`, all slots will be disconnected,
            by default `None`
        missing_ok : bool, optional
            If `False` and the provided `slot` is not connected, raises `ValueError.
            by default `True`

        Raises
        ------
        ValueError
            If `slot` is not connected and `missing_ok` is False.
        """
        for sig in self._signals.values():
            sig.disconnect(slot, missing_ok)
        super().disconnect(slot, missing_ok)

    def _slot_index(self, slot: Callable) -> int:
        """Get index of `slot` in `self._slots`. Return -1 if not connected.

        In interpreted mode, `_relay_partial` callbacks are stored as
        weak references to the callable object itself, so comparing the
        dereferenced callback to the provided `_relay_partial` works. In compiled
        mode (mypyc), `weak_callback` may normalize a `_relay_partial` to a strong
        reference to its `__call__` method (a MethodWrapperType), to avoid segfaults on
        garbage collection. In that case the default WeakCallback equality logic is the
        correct and more robust path.

        Therefore, try the base implementation first (which compares normalized
        WeakCallback objects). If that fails and we're dealing with a
        `_relay_partial`, fall back to comparing the dereferenced callable to the
        provided slot for backward compatibility.
        """
        # First, try the standard equality path used by SignalInstance
        idx = super()._slot_index(slot)
        if idx != -1:
            return idx

        # Fallback: handle direct comparison for `_relay_partial` instances
        if isinstance(slot, _relay_partial):
            with self._lock:
                for i, s in enumerate(self._slots):
                    deref = s.dereference()
                    # Case 1: stored deref is the _relay_partial itself (interpreted)
                    if deref == slot:
                        return i
                    # Case 2: compiled path where we stored __call__ bound method
                    # (these will never hit on codecov, but they are covered in tests)
                    owner = getattr(deref, "__self__", None)  # pragma: no cover
                    if (
                        isinstance(owner, _relay_partial) and owner == slot
                    ):  # pragma: no cover
                        return i
        return -1  # pragma: no cover


# NOTE
# To developers. Avoid adding public names to this class, as it is intended to be
# a container for user-determined names.  If names must be added, try to prefix
# with "psygnal_" to avoid conflicts with user-defined names.
@mypyc_attr(allow_interpreted_subclasses=True)
class SignalGroup:
    """A collection of signals that can be connected to as a single unit.

    This class is not intended to be instantiated directly.  Instead, it should be
    subclassed, and the subclass should define Signal instances as class attributes.
    The SignalGroup will then automatically collect these signals and provide a
    SignalRelay instance (at `group.all`) that can be used to connect to all of the
    signals in the group.

    This class is used in both the EventedModels and the evented dataclass patterns.
    See also: `psygnal.SignalGroupDescriptor`, which provides convenient and explicit
    way to create a SignalGroup on a dataclass-like class.

    Parameters
    ----------
    instance : Any, optional
        An object to which this `SignalGroup` is bound, by default None

    Attributes
    ----------
    all : SignalRelay
        A special SignalRelay instance that can be used to connect to all signals in
        this group.

    Examples
    --------
    ```python
    from psygnal import Signal, SignalGroup


    class MySignals(SignalGroup):
        sig1 = Signal()
        sig2 = Signal()


    group = MySignals()
    group.all.connect(print)  # connect to all signals in the group

    list(group)  # ['sig1', 'sig2']
    len(group)  # 2
    group.sig1 is group["sig1"]  # True
    ```
    """

    _psygnal_signals: ClassVar[Mapping[str, Signal]]
    _psygnal_uniform: ClassVar[bool] = False
    _psygnal_name_conflicts: ClassVar[set[str]]
    _psygnal_aliases: ClassVar[dict[str, str | None]]

    _psygnal_instances: dict[str, SignalInstance]

    def __init__(self, instance: Any = None) -> None:
        cls = type(self)
        if not hasattr(cls, "_psygnal_signals"):
            raise TypeError(
                "Cannot instantiate `SignalGroup` directly.  Use a subclass instead."
            )

        self._psygnal_instances = {
            name: (
                sig._create_signal_instance(self)
                if name in cls._psygnal_name_conflicts
                else sig.__get__(self, cls)
            )
            for name, sig in cls._psygnal_signals.items()
        }
        self._psygnal_relay = SignalRelay(self._psygnal_instances, instance)

    def __init_subclass__(
        cls,
        strict: bool = False,
        signal_aliases: Mapping[str, str | None] = {},
    ) -> None:
        """Collects all Signal instances on the class under `cls._psygnal_signals`."""
        # Collect Signals and remove from class attributes
        # Use dir(cls) instead of cls.__dict__ to get attributes from super()
        forbidden = {
            k for k in getattr(cls, "__dict__", ()) if k.startswith("_psygnal")
        }
        if forbidden:
            raise TypeError(
                f"SignalGroup subclass cannot have attributes starting with '_psygnal'."
                f" Found: {forbidden}"
            )

        _psygnal_signals = {}
        for k in dir(cls):
            val = getattr(cls, k, None)
            if isinstance(val, Signal):
                _psygnal_signals[k] = val

        # Collect the Signals also from super-class
        # When subclassing, the Signals have been removed from the attributes,
        # look for cls._psygnal_signals also
        cls._psygnal_signals = {
            **getattr(cls, "_psygnal_signals", {}),
            **_psygnal_signals,
        }

        # Emit warning for signal names conflicting with SignalGroup attributes
        reserved = set(dir(SignalGroup))
        cls._psygnal_name_conflicts = conflicts = {
            k
            for k in cls._psygnal_signals
            if k in reserved or k.startswith(("_psygnal", "psygnal"))
        }
        if conflicts:
            for name in conflicts:
                if isinstance(getattr(cls, name), Signal):
                    delattr(cls, name)
            Names = "Names" if len(conflicts) > 1 else "Name"
            Are = "are" if len(conflicts) > 1 else "is"
            warnings.warn(
                f"{Names} {sorted(conflicts)!r} {Are} reserved. You cannot use these "
                "names to access SignalInstances as attributes on a SignalGroup. (You "
                "may still access them as keys to __getitem__: `group['name']`).",
                UserWarning,
                stacklevel=2,
            )

        aliases = getattr(cls, "_psygnal_aliases", {})
        cls._psygnal_aliases = {**aliases, **signal_aliases}
        cls._psygnal_uniform = _is_uniform(cls._psygnal_signals.values())
        if strict and not cls._psygnal_uniform:
            raise TypeError(
                "All Signals in a strict SignalGroup must have the same signature"
            )
        super().__init_subclass__()

    @property
    def instance(self) -> Any:
        """Object that owns this `SignalGroup`."""
        return self._psygnal_relay.instance

    @property
    def all(self) -> SignalRelay:
        """SignalInstance that can be used to connect to all signals in this group.

        Examples
        --------
        ```python
        from psygnal import Signal, SignalGroup


        class MySignals(SignalGroup):
            sig1 = Signal()
            sig2 = Signal()


        group = MySignals()
        group.sig2.connect(...)  # connect to a single signal by name
        group.all.connect(...)  # connect to all signals in the group
        ```
        """
        return self._psygnal_relay

    @property
    def signals(self) -> Mapping[str, SignalInstance]:
        """A mapping of signal names to SignalInstance instances."""
        # TODO: deprecate this property
        # warnings.warn(
        #     "Accessing the `signals` property on a SignalGroup is deprecated. "
        #     "Use __iter__ to iterate over all signal names, and __getitem__ or "
        #     "getattr to access signal instances. This will be an error in a future.",
        #     FutureWarning,
        #     stacklevel=2,
        # )
        return MappingProxyType(self._psygnal_instances)

    def __len__(self) -> int:
        """Return the number of signals in the group (not including the relay)."""
        return len(self._psygnal_instances)

    def __getitem__(self, item: str) -> SignalInstance:
        """Get a signal instance by name."""
        return self._psygnal_instances[item]

    # this is just here for type checking, particularly on cases
    # where the SignalGroup comes from the SignalGroupDescriptor
    # (such as in evented dataclasses).  In those cases, it's hard to indicate
    # to mypy that all remaining attributes are SignalInstances.
    def __getattr__(self, __name: str) -> SignalInstance:
        """Get a signal instance by name."""
        raise AttributeError(  # pragma: no cover
            f"{type(self).__name__!r} object has no attribute {__name!r}"
        )

    def __iter__(self) -> Iterator[str]:
        """Yield the names of all signals in the group."""
        return iter(self._psygnal_instances)

    def __contains__(self, item: str) -> bool:
        """Return True if the group contains a signal with the given name."""
        # this is redundant with __iter__ and can be removed, but only after
        # removing the deprecation warning in __getattr__
        return item in self._psygnal_instances

    def __repr__(self) -> str:
        """Return repr(self)."""
        name = self.__class__.__name__

        if self.instance is not None:
            owner_type = type(self.instance).__name__
            owner_repr = f" on <{owner_type} instance at {id(self.instance):#x}>"
        else:
            owner_repr = ""
        return f"<SignalGroup {name!r}{owner_repr} with {len(self)} signals>"

    @classmethod
    def psygnals_uniform(cls) -> bool:
        """Return true if all signals in the group have the same signature."""
        return cls._psygnal_uniform

    @classmethod
    def is_uniform(cls) -> bool:
        """Return true if all signals in the group have the same signature."""
        warnings.warn(
            "The `is_uniform` method on SignalGroup is deprecated. Use "
            "`psygnals_uniform` instead. This will be an error in v0.11.",
            FutureWarning,
            stacklevel=2,
        )
        return cls._psygnal_uniform

    def __deepcopy__(self, memo: dict[int, Any]) -> SignalGroup:
        # TODO:
        # This really isn't a deep copy. Should we also copy connections?
        # a working deepcopy is important for pydantic support, but in most cases
        # it will be a group without any signals connected
        return type(self)(instance=self._psygnal_relay.instance)

    # The rest are passthrough methods to the SignalRelay.
    # The full signatures are here to make mypy and IDEs happy.
    # parity with SignalInstance methods is tested in test_group.py

    @overload
    def connect(
        self,
        *,
        thread: threading.Thread | Literal["main", "current"] | None = ...,
        check_nargs: bool | None = ...,
        check_types: bool | None = ...,
        unique: bool | Literal["raise"] = ...,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = ...,
        priority: int = ...,
    ) -> Callable[[F], F]: ...

    @overload
    def connect(
        self,
        slot: F,
        *,
        thread: threading.Thread | Literal["main", "current"] | None = ...,
        check_nargs: bool | None = ...,
        check_types: bool | None = ...,
        unique: bool | Literal["raise"] = ...,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = ...,
        priority: int = ...,
    ) -> F: ...

    def connect(
        self,
        slot: F | None = None,
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | Literal["raise"] = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
        emit_on_evented_child_events: bool = False,
    ) -> Callable[[F], F] | F:
        if slot is None:
            return self._psygnal_relay.connect(
                thread=thread,
                check_nargs=check_nargs,
                check_types=check_types,
                unique=unique,
                max_args=max_args,
                on_ref_error=on_ref_error,
                priority=priority,
                emit_on_evented_child_events=emit_on_evented_child_events,
            )
        else:
            return self._psygnal_relay.connect(
                slot,
                thread=thread,
                check_nargs=check_nargs,
                check_types=check_types,
                unique=unique,
                max_args=max_args,
                on_ref_error=on_ref_error,
                priority=priority,
                emit_on_evented_child_events=emit_on_evented_child_events,
            )

    def connect_direct(
        self,
        slot: Callable | None = None,
        *,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | Literal["raise"] = False,
        max_args: int | None = None,
    ) -> Callable[[Callable], Callable] | Callable:
        return self._psygnal_relay.connect_direct(
            slot,
            check_nargs=check_nargs,
            check_types=check_types,
            unique=unique,
            max_args=max_args,
        )

    def disconnect(self, slot: Callable | None = None, missing_ok: bool = True) -> None:
        return self._psygnal_relay.disconnect(slot=slot, missing_ok=missing_ok)

    def block(self, exclude: Container[str | SignalInstance] = ()) -> None:
        return self._psygnal_relay.block(exclude=exclude)

    def unblock(self) -> None:
        return self._psygnal_relay.unblock()

    def blocked(
        self, exclude: Container[str | SignalInstance] = ()
    ) -> AbstractContextManager[None]:
        return self._psygnal_relay.blocked(exclude=exclude)

    def pause(self) -> None:
        return self._psygnal_relay.pause()

    def resume(self, reducer: ReducerFunc | None = None, initial: Any = _NULL) -> None:
        return self._psygnal_relay.resume(reducer=reducer, initial=initial)

    def paused(
        self, reducer: ReducerFunc | None = None, initial: Any = _NULL
    ) -> AbstractContextManager[None]:
        return self._psygnal_relay.paused(reducer=reducer, initial=initial)


def _is_uniform(signals: Iterable[Signal]) -> bool:
    """Return True if all signals have the same signature."""
    seen: set[tuple[str, ...]] = set()
    for s in signals:
        v = tuple(str(p.annotation) for p in s.signature.parameters.values())
        if seen and v not in seen:  # allow zero or one
            return False
        seen.add(v)
    return True


class _relay_partial:
    """Small, single-purpose, mypyc-friendly variant of functools.partial.

    Used to call SignalRelay._slot_relay with a specific loc.
    __hash__ and __eq__ are implemented to make this object hashable and
    comparable to other _relay_partial objects, so that adding it to a set
    twice will not create two separate entries.
    """

    __slots__ = ("loc", "relay")

    def __init__(self, relay: SignalRelay, loc: PathStep | None = None) -> None:
        self.relay = relay
        self.loc = loc

    def __call__(self, *args: Any) -> Any:
        return self.relay._slot_relay(*args, loc=self.loc)

    def __hash__(self) -> int:
        return hash((self.relay, self.loc))

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, _relay_partial)
            and self.relay == other.relay
            and self.loc == other.loc
        )
