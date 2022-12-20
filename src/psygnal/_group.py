"""A SignalGroup class that allows connecting to all SignalInstances on the class.

Note that unlike a slot/callback connected to SignalInstance.connect, a slot connected
to SignalGroup.connect does *not* receive the direct arguments that were emitted by a
given SignalInstance. Instead, the slot/callback will receive an EmissionInfo named
tuple, which contains `.signal`: the SignalInstance doing the emitting, and `.args`:
the args that were emitted.

"""
from __future__ import annotations

from typing import (
    Any,
    Callable,
    ClassVar,
    ContextManager,
    Iterable,
    Mapping,
    NamedTuple,
)

from mypy_extensions import mypyc_attr

from psygnal._signal import Signal, SignalInstance, _SignalBlocker

__all__ = ["EmissionInfo", "SignalGroup"]


class EmissionInfo(NamedTuple):
    """Tuple containing information about an emission event.

    Attributes
    ----------
    signal : SignalInstance
    args: tuple
    """

    signal: SignalInstance
    args: tuple[Any, ...]


@mypyc_attr(allow_interpreted_subclasses=True)
class SignalGroup(SignalInstance):
    """`SignalGroup` that enables connecting to all `SignalInstances`.

    Parameters
    ----------
    instance : Any, optional
        An instance to which this event group is bound, by default None
    name : str, optional
        Optional name for this event group, by default will be the name of the group
        subclass.  (e.g., 'Events' in the example below.)

    Examples
    --------
    >>> class Events(SignalGroup):
    ...     sig1 = Signal(str)
    ...     sig2 = Signal(str)
    ...
    >>> events = Events()
    ...
    >>> def some_callback(record):
    ...     record.signal  # the SignalInstance that emitted
    ...     record.args    # the args that were emitted
    ...
    >>> events.connect(some_callback)

    note that the `SignalGroup` may also be created with `strict=True`, which will
    enforce that *all* signals have the same emission signature

    This is ok:

    >>> class Events(SignalGroup, strict=True):
    ...     sig1 = Signal(int)
    ...     sig1 = Signal(int)

    This will raise an exception

    >>> class Events(SignalGroup, strict=True):
    ...     sig1 = Signal(int)
    ...     sig1 = Signal(str)  # not the same signature
    """

    _signals_: ClassVar[Mapping[str, Signal]]
    _uniform: ClassVar[bool] = False

    def __len__(self) -> int:
        return len(self._slots)

    def __init_subclass__(cls, strict: bool = False) -> None:
        """Finds all Signal instances on the class and add them to `cls._signals_`."""
        cls._signals_ = {}
        for k in dir(cls):
            v = getattr(cls, k)
            if isinstance(v, Signal):
                cls._signals_[k] = v
        _sigs = {
            tuple(p.annotation for p in s.signature.parameters.values())
            for s in cls._signals_.values()
        }
        cls._uniform = len(_sigs) == 1
        if strict and not cls._uniform:
            raise TypeError(
                "All Signals in a strict SignalGroup must have the same signature"
            )

        return super().__init_subclass__()

    def __init__(self, instance: Any = None, name: str | None = None) -> None:
        super().__init__(
            signature=(EmissionInfo,),
            instance=instance,
            name=name or self.__class__.__name__,
        )
        self._sig_was_blocked: dict[str, bool] = {}
        for _, sig in self.signals.items():
            sig.connect(self._slot_relay, check_nargs=False, check_types=False)

    @property
    def signals(self) -> dict[str, SignalInstance]:
        """Return {name -> SignalInstance} map of all signal instances in this group."""
        return {n: getattr(self, n) for n in type(self)._signals_}

    @classmethod
    def is_uniform(cls) -> bool:
        """Return true if all signals in the group have the same signature."""
        return cls._uniform

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
            for sig in self.signals.values():
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
        for k, v in self.signals.items():
            if exclude and v in exclude or k in exclude:
                continue
            self._sig_was_blocked[k] = v._is_blocked
            v.block()

    def unblock(self) -> None:
        """Unblock this signal and all emitters, allowing them to emit."""
        super().unblock()
        for k, v in self.signals.items():
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
        for signal in self.signals.values():
            signal.disconnect(slot, missing_ok)
        super().disconnect(slot, missing_ok)

    def __repr__(self) -> str:
        """Return repr(self)."""
        name = f" {self.name!r}" if self.name else ""
        instance = f" on {self.instance!r}" if self.instance else ""
        nsignals = len(self.signals)
        signals = f"{nsignals} signals" if nsignals > 1 else ""
        return f"<SignalGroup{name} with {signals}{instance}>"


# _doc = SignalGroup.connect.__doc__.split("Parameters")[-1]  # type: ignore


# SignalGroup.connect.__doc__ = (
#     """
#         Connect `slot` to be called whenever *any* Signal in this group is emitted.

#         Note that unlike a slot/callback connected to `SignalInstance.connect`, a slot
#         connected to `SignalGroup.connect` does *not* receive the direct arguments
#         that were emitted by a given `SignalInstance` in the group. Instead, the
#         slot/callback will receive an `EmissionInfo` named tuple, which contains
#         `.signal`: the SignalInstance doing the emitting, `.args`: the args that were
#         emitted.

#         This method may be used as a decorator.

#             @group.connect
#             def my_function(): ...

#         Parameters
# """.strip()
#     + _doc
# )
