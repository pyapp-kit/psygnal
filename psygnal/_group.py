"""A SignalGroup class that allows connecting to all SignalInstances on the class.

Note that unlike a slot/callback connected to SignalInstance.connect, a slot connected
to SignalGroup.connect does *not* receive the direct arguments that were emitted by a
given SignalInstance. Instead, the slot/callback will receive an EmissionInfo named
tuple, which contains `.signal`: the SignalInstance doing the emitting, and `.args`:
the args that were emitted.

"""
from typing import Any, Callable, Dict, NamedTuple, Optional, Tuple, Union

from psygnal._signal import Signal, SignalInstance

__all__ = ["EmissionInfo", "SignalGroup"]


class EmissionInfo(NamedTuple):
    """Tuple containing information about an emission event."""

    signal: SignalInstance
    args: Tuple[Any, ...]
    extra_info: Dict[str, Any] = {}


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


class SignalGroup(SignalInstance, metaclass=_SignalGroupMeta):
    """SignalGroup that enables connecting to all SignalInstances.

    Example
    -------
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

    note that the SignalGroup may also be created with `strict=True`, which will
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

    @property
    def signals(self) -> Dict[str, SignalInstance]:
        """Return {name -> SignalInstance} map of all signal instances in this group."""
        return {n: getattr(self, n) for n in type(self)._signals_}

    @classmethod
    @property
    def is_uniform(cls) -> bool:
        """Return true if SignalGroup is uniform (all signals have same signature)."""
        return cls._uniform

    def connect(
        self, slot: Optional[InfoSlot] = None, **extra_info: Any
    ) -> Union[Callable[[Callable], Callable], Callable]:
        """Connect `slot` to be called whenever *any* Signal in this group is emitted.

        Note that unlike a slot/callback connected to SignalInstance.connect, a slot
        connected to `SignalGroup.connect` does *not* receive the direct arguments that
        were emitted by a given `SignalInstance`. Instead, the slot/callback will
        receive an `EmissionInfo` named tuple, which contains `.signal`: the
        SignalInstance doing the emitting, `.args`: the args that were emitted, and
        `extra_info`: a dict of any additional keyword args passed to `connect`.

        Parameters
        ----------
        slot : callable, optional
            A callback to be called whenever any signal is emitted.
            Will receive an `EmissionInfo` named tuple.

        Returns
        -------
        callable
            the same slot provided (i.e. can be used as a decorator)
        """

        def _inner(slot: InfoSlot) -> InfoSlot:
            for sig in self.signals.values():

                def _slotwrapper(
                    *args: Any, _slot: InfoSlot = slot, _sig: SignalInstance = sig
                ) -> Any:
                    info = EmissionInfo(_sig, args, extra_info)
                    return _slot(info)

                sig.connect(_slotwrapper, check_nargs=False, check_types=False)
            return slot

        return _inner if slot is None else _inner(slot)

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

        Params are the same as {meth}`~psygnal.SignalInstance.connect`


        Parameters
        ----------
        slot : Callable
            A callable to connect to this signal.  If the callable accepts less
            arguments than the signature of this slot, then they will be discarded when
            calling the slot.
        check_nargs : bool, optional
            If `True` and the provided `slot` requires more positional arguments than
            the signature of this Signal, raise `TypeError`. by default `True`.
        check_types : bool, optional
            If `True`, An additional check will be performed to make sure that types
            declared in the slot signature are compatible with the signature
            declared by this signal, by default `False`.
        unique : bool or str, optional
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
