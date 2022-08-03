"""A SignalGroup class that allows connecting to all SignalInstances on the class.

Note that unlike a slot/callback connected to SignalInstance.connect, a slot connected
to SignalGroup.connect does *not* receive the direct arguments that were emitted by a
given SignalInstance. Instead, the slot/callback will receive an EmissionInfo named
tuple, which contains `.signal`: the SignalInstance doing the emitting, and `.args`:
the args that were emitted.

"""
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterable, Iterator, Optional, Tuple, Union

from psygnal._signal import NormedCallback, Signal, SignalInstance

__all__ = ["EmissionInfo", "SignalGroup"]


# this is a variant of a NamedTuple that works with Cython<3.0a7
class EmissionInfo(tuple):
    """Tuple containing information about an emission event.

    Attributes
    ----------
    signal : SignalInstance
    args: tuple
    """

    signal: SignalInstance
    args: Tuple[Any, ...]

    def __new__(cls, signal: SignalInstance, args: Tuple[Any, ...]) -> "EmissionInfo":
        """Create new object."""
        obj = tuple.__new__(cls, (signal, args))
        obj.signal = signal
        obj.args = args
        return obj

    def __repr__(self) -> str:  # pragma: no cover
        """Return repr(self)."""
        return f"EmissionInfo(signal={self.signal}, args={self.args})"


class _SignalGroupMeta(type):
    _signals_: Dict[str, Signal]
    _uniform: bool = False

    def __new__(
        mcls: type,
        name: str,
        bases: tuple,
        namespace: dict,
        strict: bool = False,
        **kwargs: Any,
    ) -> "_SignalGroupMeta":
        cls: _SignalGroupMeta = type.__new__(mcls, name, bases, namespace)
        cls._signals_ = {k: v for k, v in namespace.items() if isinstance(v, Signal)}
        _sigs = {
            tuple(p.annotation for p in s.signature.parameters.values())
            for s in cls._signals_.values()
        }
        cls._uniform = len(_sigs) == 1
        if strict and not cls._uniform:
            raise TypeError(
                "All Signals in a strict SignalGroup must have the same signature"
            )
        return cls


InfoSlot = Callable[[EmissionInfo], None]
OptionalInfoSlot = Union[InfoSlot, Callable[[], None]]


class SignalGroup(SignalInstance, metaclass=_SignalGroupMeta):
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

    __slots__ = ("_instance", "_name", "_is_blocked", "_is_paused", "_sig_was_blocked")

    def __init__(self, instance: Any = None, name: Optional[str] = None) -> None:
        super().__init__(
            signature=(EmissionInfo,),
            instance=instance,
            name=name or self.__class__.__name__,
        )
        self._sig_was_blocked: Dict[str, bool] = {}
        for _, sig in self.signals.items():
            sig.connect(self._slot_relay, check_nargs=False, check_types=False)

    @property
    def signals(self) -> Dict[str, SignalInstance]:
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
        slot: Optional[Callable] = None,
        *,
        check_nargs: Optional[bool] = None,
        check_types: Optional[bool] = None,
        unique: Union[bool, str] = False,
        max_args: Optional[int] = None,
    ) -> Union[Callable[[Callable], Callable], Callable]:
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

    def block(self, exclude: Iterable[Union[str, SignalInstance]] = ()) -> None:
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

    @contextmanager
    def blocked(
        self, exclude: Iterable[Union[str, SignalInstance]] = ()
    ) -> Iterator[None]:
        """Provide context manager to temporarly block all emitters in this group.

        Parameters
        ----------
        exclude : iterable of str or SignalInstance, optional
            An iterable of signal instances or names to exempt from the block,
            by default ()
        """
        self.block(exclude=exclude)
        try:
            yield
        finally:
            self.unblock()

    def disconnect(
        self, slot: Optional[NormedCallback] = None, missing_ok: bool = True
    ) -> None:
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
        signals = f"{nsignals} signal" + "s" if nsignals > 1 else ""
        return f"<SignalGroup{name} with {signals}{instance}>"


_doc = SignalGroup.connect.__doc__.split("Parameters")[-1]  # type: ignore


SignalGroup.connect.__doc__ = (
    """
        Connect `slot` to be called whenever *any* Signal in this group is emitted.

        Note that unlike a slot/callback connected to `SignalInstance.connect`, a slot
        connected to `SignalGroup.connect` does *not* receive the direct arguments that
        were emitted by a given `SignalInstance` in the group. Instead, the
        slot/callback will receive an `EmissionInfo` named tuple, which contains
        `.signal`: the SignalInstance doing the emitting, `.args`: the args that were
        emitted.

        This method may be used as a decorator.

            @group.connect
            def my_function(): ...

        Parameters
""".strip()
    + _doc
)
