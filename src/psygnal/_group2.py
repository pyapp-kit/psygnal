from __future__ import annotations

from typing import (
    Any,
    Callable,
    ClassVar,
    ContextManager,
    Iterable,
    Iterator,
    Mapping,
    NamedTuple,
)

from mypy_extensions import mypyc_attr

from psygnal._signal import Signal, SignalInstance, _SignalBlocker


class EmissionInfo(NamedTuple):
    """Tuple containing information about an emission event.

    Attributes
    ----------
    signal : SignalInstance
    args: tuple
    """

    signal: SignalInstance
    args: tuple[Any, ...]


class SignalRelay(SignalInstance):
    """Special SignalInstance that can be used to connect to all signals in a group."""

    def __init__(self, group: SignalGroup, instance: Any = None) -> None:
        self._group = group
        super().__init__(signature=(EmissionInfo,), instance=instance)
        self._sig_was_blocked: dict[str, bool] = {}
        for sig in group._psygnal_instances.values():
            sig.connect(self._slot_relay, check_nargs=False, check_types=False)

    def _slot_relay(self, *args: Any) -> None:
        emitter = Signal.current_emitter()
        if emitter:
            info = EmissionInfo(emitter, args)
            self._run_emit_loop((info,))

    def connect_direct(
        self,
        slot: Callable | None = None,
        *,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
    ) -> Callable[[Callable], Callable] | Callable:
        """Connect `slot` to be called whenever *any* Signal in this group is emitted.

        Params are the same as {meth}`~psygnal.SignalInstance.connect`.  It's probably
        best to check whether `self.is_uniform()`

        Parameters
        ----------
        slot : Callable
            A callable to connect to this signal.  If the callable accepts less
            arguments than the signature of this slot, then they will be discarded when
            calling the slot.
        check_nargs : Optional[bool]
            If `True` and the provided `slot` requires more positional arguments than
            the signature of this Signal, raise `TypeError`. by default `True`.
        check_types : Optional[bool]
            If `True`, An additional check will be performed to make sure that types
            declared in the slot signature are compatible with the signature
            declared by this signal, by default `False`.
        unique : Union[bool, str]
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
            for sig in self._group.values():
                sig.connect(
                    slot,
                    check_nargs=check_nargs,
                    check_types=check_types,
                    unique=unique,
                    max_args=max_args,
                )
            return slot

        return _inner if slot is None else _inner(slot)

    def block(self, exclude: Iterable[str | SignalInstance] = ()) -> None:
        """Block this signal and all emitters from emitting."""
        super().block()
        for k, v in self._group.items():
            if exclude and v in exclude or k in exclude:
                continue
            self._sig_was_blocked[k] = v._is_blocked
            v.block()

    def unblock(self) -> None:
        """Unblock this signal and all emitters, allowing them to emit."""
        super().unblock()
        for k, v in self._group.items():
            if not self._sig_was_blocked.pop(k, False):
                v.unblock()

    def blocked(
        self, exclude: Iterable[str | SignalInstance] = ()
    ) -> ContextManager[None]:
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
        for signal in self._group.values():
            signal.disconnect(slot, missing_ok)
        super().disconnect(slot, missing_ok)


@mypyc_attr(allow_interpreted_subclasses=True)
class SignalGroup(Mapping[str, SignalInstance]):
    _signals_: ClassVar[Mapping[str, Signal]]
    _uniform: ClassVar[bool] = False

    all: SignalRelay  # but, can be modified at instantiation

    def __init__(self, instance: Any = None, relay_name: str = "all") -> None:
        cls = type(self)
        if not hasattr(cls, "_signals_"):
            raise TypeError(
                "Cannot instantiate SignalGroup directly.  Use a subclass instead."
            )
        self._psygnal_instances: dict[str, SignalInstance] = {
            name: signal.__get__(self, cls) for name, signal in cls._signals_.items()
        }
        self._psygnal_relay = SignalRelay(self, instance)
        setattr(self, relay_name, self._psygnal_relay)

    def __init_subclass__(cls, strict: bool = False) -> None:
        """Finds all Signal instances on the class and add them to `cls._signals_`."""
        cls._signals_ = {
            k: val
            for k, val in getattr(cls, "__dict__", {}).items()
            if isinstance(val, Signal)
        }

        cls._uniform = _is_uniform(cls._signals_.values())
        if strict and not cls._uniform:
            raise TypeError(
                "All Signals in a strict SignalGroup must have the same signature"
            )
        super().__init_subclass__()

    def __getattr__(self, name: str) -> Signal:
        if name in self._signals_:
            return self._signals_[name]
        if name == "signals":  # for backwards compatibility
            # TODO: add deprecation warning
            return self._psygnal_instances  # type: ignore
        if name != "_psygnal_relay" and hasattr(self._psygnal_relay, name):
            # TODO: add deprecation warning and redirect to `self.all`
            return getattr(self._psygnal_relay, name)  # type: ignore
        raise AttributeError(f"{type(self).__name__!r} has no attribute {name!r}")

    def __len__(self) -> int:
        return len(self._signals_)

    def __getitem__(self, item: str) -> SignalInstance:
        return self._psygnal_instances[item]

    def __iter__(self) -> Iterator[str]:
        return iter(self._signals_)

    def __repr__(self) -> str:
        """Return repr(self)."""
        name = self.__class__.__name__
        instance = ""
        nsignals = len(self)
        signals = f"{nsignals} signals"
        return f"<SignalGroup {name!r} with {signals}{instance}>"

    @classmethod
    def is_uniform(cls) -> bool:
        """Return true if all signals in the group have the same signature."""
        # TODO: Deprecate this method
        return cls._uniform


def _is_uniform(signals: Iterable[Signal]) -> bool:
    """Return True if all signals have the same signature."""
    seen: set[tuple[str, ...]] = set()
    for s in signals:
        v = tuple(str(p.annotation) for p in s.signature.parameters.values())
        if seen and v not in seen:  # allow zero or one
            return False
        seen.add(v)
    return True
