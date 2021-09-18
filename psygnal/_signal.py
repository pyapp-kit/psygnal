__all__ = ["Signal", "SignalInstance"]

import inspect
import threading
import warnings
import weakref
from contextlib import contextmanager
from functools import lru_cache
from inspect import Parameter, Signature, ismethod
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    NoReturn,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
    overload,
)

from typing_extensions import Literal

MethodRef = Tuple["weakref.ReferenceType[object]", str]
NormedCallback = Union[MethodRef, Callable]
StoredSlot = Tuple[NormedCallback, Optional[int]]
AnyType = Type[Any]


_SIG_CACHE: Dict[int, Signature] = {}


def signature(obj: Any) -> inspect.Signature:
    try:
        return inspect.signature(obj)
    except ValueError as e:
        try:
            if not inspect.ismethod(obj):  # avoid caching strong refs
                return _stub_sig(obj)
        except Exception:
            pass
        raise e


@lru_cache()
def _stub_sig(obj: Any) -> Signature:
    import builtins

    if obj is builtins.print:
        params = [
            Parameter(name="value", kind=Parameter.VAR_POSITIONAL),
            Parameter(name="sep", kind=Parameter.KEYWORD_ONLY, default=" "),
            Parameter(name="end", kind=Parameter.KEYWORD_ONLY, default="\n"),
            Parameter(name="file", kind=Parameter.KEYWORD_ONLY, default=None),
            Parameter(name="flush", kind=Parameter.KEYWORD_ONLY, default=False),
        ]
        return Signature(params)
    raise ValueError("unknown object")


class Signal:
    """Signal descriptor, for declaring a signal on a class.

    This is designed to be used as a class attribute, with the supported signature(s)
    provided in the contructor:

        class MyEmitter:
            changed = Signal(int)  # changed will emit an int

        def receiver(arg: int):
            print("new value:", arg)

        emitter = MyEmitter()
        emitter.changed.connect(receiver)
        emitter.emit(1)

    Note: in the example above, `MyEmitter.changed` is an instance of `Signal`,
    and `emitter.changed` is an instance of `SignalInstance`.

    Parameters
    ----------
    *types : sequence of Type
        A sequence of individual types
    description : str, optional
        Optional descriptive text for the signal.  (not used internally).
    name : str, optional
        Optional name of the signal. If it is not specified then the name of the
        class attribute that is bound to the signal will be used. default None
    check_nargs_on_connect : str, optional
        Whether to check the number of positional args against `signature` when
        connecting a new callback. This can also be provided at connection time using
        `.connect(..., check_nargs=True)`. By default, True.
    check_types_on_connect : str, optional
        Whether to check the callback parameter types against `signature` when
        connecting a new callback. This can also be provided at connection time using
        `.connect(..., check_types=True)`. By default, False.
    """

    __slots__ = (
        "_signal_instances",
        "_name",
        "_signature",
        "description",
        "_check_nargs_on_connect",
        "_check_types_on_connect",
    )

    if TYPE_CHECKING:  # pragma: no cover
        _signature: Signature  # callback signature for this signal
        _signal_instances: Dict[
            "Signal", weakref.WeakKeyDictionary[Any, "SignalInstance"]
        ]

    _current_emitter: Optional["SignalInstance"] = None

    def __init__(
        self,
        *types: Union[AnyType, Signature],
        description: str = "",
        name: Optional[str] = None,
        check_nargs_on_connect: bool = True,
        check_types_on_connect: bool = False,
    ) -> None:

        self._signal_instances = {}
        self._name = name
        self.description = description
        self._check_nargs_on_connect = check_nargs_on_connect
        self._check_types_on_connect = check_types_on_connect

        if types and isinstance(types[0], Signature):
            self._signature = types[0]
            if len(types) > 1:
                warnings.warn(
                    "Only a single argument is accepted when directly providing a"
                    f" `Signature`.  These args were ignored: {types[1:]}"
                )
        else:
            self._signature = _build_signature(*cast(Tuple[AnyType, ...], types))

    @property
    def signature(self) -> Signature:
        """Signature supported by this Signal."""
        return self._signature

    def __set_name__(self, owner: AnyType, name: str) -> None:
        """Set name of signal when declared as a class attribute on `owner`."""
        if self._name is None:
            self._name = name

    def __getattr__(self, name: str) -> Any:
        """Get attribute. Provide useful error if trying to get `connect`."""
        if name == "connect":
            name = self.__class__.__name__
            raise AttributeError(
                f"{name!r} object has no attribute 'connect'. You can connect to the "
                "signal on the *instance* of a class with a Signal() class attribute. "
                "Or create a signal instance directly with SignalInstance."
            )
        return self.__getattribute__(name)

    @overload
    def __get__(
        self, instance: None, owner: Optional[AnyType] = None
    ) -> "Signal":  # noqa
        ...  # pragma: no cover

    @overload
    def __get__(
        self, instance: Any, owner: Optional[AnyType] = None
    ) -> "SignalInstance":  # noqa
        ...  # pragma: no cover

    def __get__(
        self, instance: Any, owner: AnyType = None
    ) -> Union["Signal", "SignalInstance"]:
        """Get signal instance.

        This is called when accessing a Signal instance.  If accessed as an
        attribute on the class `owner`, instance, will be `None`.  Otherwise,
        if `instance` is not None, we're being accessed on an instance of `owner`.

            class Emitter:
                signal = Signal()

            e = Emitter()

            E.signal  # instance will be None, owner will be Emitter
            e.signal  # instance will be e, owner will be Emitter

        Returns
        -------
        Signal or SignalInstance
            Depending on how this attribute is accessed.
        """
        if instance is None:
            return self
        d = self._signal_instances.setdefault(self, weakref.WeakKeyDictionary())
        return d.setdefault(
            instance,
            SignalInstance(
                self.signature,
                instance=instance,
                name=self._name,
                check_nargs_on_connect=self._check_nargs_on_connect,
                check_types_on_connect=self._check_types_on_connect,
            ),
        )

    @classmethod
    @contextmanager
    def _emitting(cls, emitter: "SignalInstance") -> Iterator[None]:
        """Context that sets the sender on a receiver object while emitting a signal."""
        previous, cls._current_emitter = cls._current_emitter, emitter
        try:
            yield
        finally:
            cls._current_emitter = previous

    @classmethod
    def current_emitter(cls) -> Optional["SignalInstance"]:
        """Return currently emitting SignalInstance, if any."""
        return cls._current_emitter

    @classmethod
    def sender(cls) -> Any:
        """Return currently emitting object, if any."""
        return getattr(cls._current_emitter, "instance", None)


class SignalInstance:
    """A signal instance (optionally) bound to an object.

    Normally this object will be instantiated by the `Signal.__get__` method when a
    `Signal` instance is accessed from an *instance* of a class with Signal attribute.

        class Emitter:
            signal = Signal()

        e = Emitter()

        # this next line returns: `SignalInstance(Signature(), e, 'signal')`
        e.signal

    Parameters
    ----------
    signature : inspect.Signature, optional
        The signature that this signal accepts and will emit, by default `Signature()`.
    instance : Any, optional
        An object to which this signal is bound. Normally this will be provied by the
        `Signal.__get__` method (see above).  However, an unbound `SignalInstance`
        may also be created directly. by default `None`.
    name : str, optional
        An optional name for this signal.  Normally this will be provided by the
        `Signal.__get__` method. by default `None`
    check_nargs_on_connect : str, optional
        Whether to check the number of positional args against `signature` when
        connecting a new callback. This can also be provided at connection time using
        `.connect(..., check_nargs=True)`. By default, True.
    check_types_on_connect : str, optional
        Whether to check the callback parameter types against `signature` when
        connecting a new callback. This can also be provided at connection time using
        `.connect(..., check_types=True)`. By default, False.

    Raises
    ------
    TypeError
        If `signature` is neither an instance of `inspect.Signature`, or a `tuple`
        of `type`s.
    """

    __slots__ = (
        "_signature",
        "_instance",
        "_name",
        "_slots",
        "_is_blocked",
        "_lock",
        "_check_nargs_on_connect",
        "_check_types_on_connect",
    )

    def __init__(
        self,
        signature: Signature = Signature(),
        *,
        instance: Any = None,
        name: Optional[str] = None,
        check_nargs_on_connect: bool = True,
        check_types_on_connect: bool = False,
    ) -> None:
        if isinstance(signature, (list, tuple)):
            signature = _build_signature(*signature)
        elif not isinstance(signature, Signature):  # pragma: no cover
            raise TypeError(
                "`signature` must be either a sequence of types, or an "
                "instance of `inspect.Signature`"
            )

        self._signature = signature
        self._instance: Any = instance
        self._check_nargs_on_connect = check_nargs_on_connect
        self._check_types_on_connect = check_types_on_connect
        self._name = name
        self._slots: List[StoredSlot] = []
        self._is_blocked: bool = False
        self._lock = threading.RLock()

    @property
    def signature(self) -> Signature:
        """Signature supported by this `SignalInstance`."""
        return self._signature

    @property
    def instance(self) -> Any:
        """Object that emits this `SignalInstance`."""
        return self._instance

    @property
    def name(self) -> Optional[str]:
        """Name of this `SignalInstance`."""
        return self._name or ""

    def __repr__(self) -> str:
        """Return repr."""
        name = f" {self.name!r}" if self.name else ""
        instance = f" on {self.instance!r}" if self.instance else ""
        return f"<{type(self).__name__}{name}{instance}>"

    @overload
    def connect(
        self,
        *,
        check_nargs: Optional[bool] = ...,
        check_types: Optional[bool] = ...,
        unique: Union[bool, str] = ...,
    ) -> Callable[[Callable], Callable]:
        ...  # pragma: no cover

    @overload
    def connect(
        self,
        slot: Callable,
        *,
        check_nargs: Optional[bool] = ...,
        check_types: Optional[bool] = ...,
        unique: Union[bool, str] = ...,
    ) -> Callable:
        ...  # pragma: no cover

    # TODO: allow connect as decorator with arguments
    def connect(
        self,
        slot: Optional[Callable] = None,
        *,
        check_nargs: Optional[bool] = None,
        check_types: Optional[bool] = None,
        unique: Union[bool, str] = False,
    ) -> Union[Callable[[Callable], Callable], Callable]:
        """Connect a callback ("slot") to this signal.

        `slot` is compatible if:
            - it has equal or less required positional arguments.
            - it has no required keyword arguments
            - if `check_types` is True, all provided types must match

        This method may be used as a decorator.

            @signal.connect
            def my_function(): ...

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

        Raises
        ------
        TypeError
            If a non-callable object is provided.
        ValueError
            If the provided slot fails validation, either due to mismatched positional
            argument requirements, or failed type checking.
        ValueError
            If `unique` is `True` and `slot` has already been connected.
        """
        if check_nargs is None:
            check_nargs = self._check_nargs_on_connect
        if check_types is None:
            check_types = self._check_types_on_connect

        def _wrapper(slot: Callable) -> Callable:
            if not callable(slot):
                raise TypeError(f"Cannot connect to non-callable object: {slot}")

            with self._lock:
                if unique and slot in self:
                    if unique == "raise":
                        raise ValueError(
                            "Slot already connect. Use `connect(..., unique=False)` "
                            "to allow duplicate connections"
                        )
                    return slot

                slot_sig = None
                spec = self.signature

                maxargs = None
                if check_nargs:
                    # make sure we have a compatible signature
                    # get the maximum number of arguments that we can pass to the slot
                    try:
                        slot_sig = signature(slot)
                    except ValueError as e:
                        warnings.warn(
                            f"{e}. To silence this warning, connect with "
                            "`check_nargs=False`"
                        )
                    else:
                        minargs, maxargs = _acceptable_posarg_range(slot_sig)
                        n_spec_params = len(spec.parameters)
                        # if `slot` requires more arguments than we will provide, raise.
                        if minargs > n_spec_params:
                            extra = (
                                f"- Slot requires at least {minargs} positional "
                                f"arguments, but spec only provides {n_spec_params}"
                            )
                            self._raise_connection_error(slot, extra)

                if check_types:
                    if slot_sig is None:  # pragma: no cover
                        slot_sig = signature(slot)
                    if not _parameter_types_match(slot, spec, slot_sig):
                        extra = f"- Slot types {slot_sig} do not match types in signal."
                        self._raise_connection_error(slot, extra)

                self._slots.append((self._normalize_slot(slot), maxargs))

            return slot

        return _wrapper(slot) if slot else _wrapper

    def _raise_connection_error(self, slot: Callable, extra: str = "") -> NoReturn:
        name = getattr(slot, "__name__", str(slot))
        msg = f"Cannot connect slot {name!r} with signature: {signature(slot)}:\n"
        msg += extra
        msg += f"\n\nAccepted signature: {self.signature}"
        raise ValueError(msg)

    def _normalize_slot(self, slot: NormedCallback) -> NormedCallback:
        if ismethod(slot):
            return (weakref.ref(slot.__self__), slot.__name__)  # type: ignore
        if isinstance(slot, tuple) and not isinstance(slot[0], weakref.ref):
            return (weakref.ref(slot[0]), slot[1])
        return slot

    def _slot_index(self, slot: NormedCallback) -> int:
        """Get index of `slot` in `self._slots`.  Return -1 if not connected."""
        with self._lock:
            normed = self._normalize_slot(slot)
            for i, (s, m) in enumerate(self._slots):
                if s == normed:
                    return i
            return -1

    def disconnect(
        self, slot: Optional[NormedCallback] = None, missing_ok: bool = True
    ) -> None:
        """Disconnect slot from signal.

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
        with self._lock:
            if slot is None:
                # NOTE: clearing an empty list is actually a RuntimeError in Qt
                self._slots.clear()
                return

            idx = self._slot_index(slot)
            if idx != -1:
                self._slots.pop(idx)
            elif not missing_ok:
                raise ValueError(f"slot is not connected: {slot}")

    def __contains__(self, slot: NormedCallback) -> bool:
        """Return `True` if slot is connected."""
        return self._slot_index(slot) >= 0

    def __len__(self) -> int:
        """Return number of connected slots."""
        return len(self._slots)

    @overload
    def emit(
        self,
        *args: Any,
        check_nargs: bool = False,
        check_types: bool = False,
        asynchronous: Literal[False] = False,
    ) -> None:
        ...  # pragma: no cover

    @overload
    def emit(
        self,
        *args: Any,
        check_nargs: bool = False,
        check_types: bool = False,
        asynchronous: Literal[True],
    ) -> Optional["EmitThread"]:
        # will return `None` if emitter is blocked
        ...  # pragma: no cover

    def emit(
        self,
        *args: Any,
        check_nargs: bool = False,
        check_types: bool = False,
        asynchronous: bool = False,
    ) -> Optional["EmitThread"]:
        """Emit this signal with arguments `args`.

        NOTE:
        `check_args` and `check_types` both add overhead when calling emit.

        Parameters
        ----------
        *args : Any
            These arguments will be passed when calling each slot (unless the slot
            accepts fewer arguments, in which case extra args will be discarded.)
        check_nargs : bool, optional
            If `False` and the provided arguments cannot be successfuly bound to the
            signature of this Signal, raise `TypeError`.  Incurs some overhead.
            by default False.
        check_types : bool, optional
            If `False` and the provided arguments do not match the types declared by
            the signature of this Signal, raise `TypeError`.  Incurs some overhead.
            by default False.
        asynchronous : bool, optional
            If `True`, run signal emission in another thread. by default `False`.

        Raises
        ------
        TypeError
            If `check_nargs` and/or `check_types` are `True`, and the corresponding
            checks fail.
        """
        if self._is_blocked:
            return None

        if check_nargs:
            try:
                self.signature.bind(*args)
            except TypeError as e:
                raise TypeError(
                    f"Cannot emit args {args} from signal {self!r} with "
                    f"signature {self.signature}:\n{e}"
                )

        if check_types and not _parameter_types_match(
            lambda: None, self.signature, _build_signature(*(type(a) for a in args))
        ):
            raise TypeError(
                f"Types provided to '{self.name}.emit' "
                f"{tuple(type(a).__name__ for a in args)} do not match signal "
                f"signature: {self.signature}"
            )

        if asynchronous:
            sd = EmitThread(self, args)
            sd.start()
            return sd

        self._run_emit_loop(args)
        return None

    @overload
    def __call__(
        self,
        *args: Any,
        check_nargs: bool = False,
        check_types: bool = False,
        asynchronous: Literal[False] = False,
    ) -> None:
        ...  # pragma: no cover

    @overload
    def __call__(
        self,
        *args: Any,
        check_nargs: bool = False,
        check_types: bool = False,
        asynchronous: Literal[True],
    ) -> Optional["EmitThread"]:
        # will return `None` if emitter is blocked
        ...  # pragma: no cover

    def __call__(
        self,
        *args: Any,
        check_nargs: bool = False,
        check_types: bool = False,
        asynchronous: bool = False,
    ) -> Optional["EmitThread"]:
        """Alias for `emit()`."""
        return self.emit(  # type: ignore
            *args,
            check_nargs=check_nargs,
            check_types=check_types,
            asynchronous=asynchronous,
        )

    def _run_emit_loop(self, args: Tuple[Any, ...]) -> None:

        rem: List[NormedCallback] = []
        # allow receiver to query sender with Signal.current_emitter()
        with self._lock:
            with Signal._emitting(self):
                for (slot, max_args) in self._slots:
                    if isinstance(slot, tuple):
                        _ref, method_name = slot
                        obj = _ref()
                        if obj is None:
                            rem.append(slot)  # add dead weakref
                            continue
                        cb = getattr(obj, method_name, None)
                        if cb is None:  # pragma: no cover
                            rem.append(slot)  # object has changed?
                            continue
                    else:
                        cb = slot

                    # TODO: add better exception handling
                    cb(*args[:max_args])

            for slot in rem:
                self.disconnect(slot)

        return None

    def block(self) -> None:
        """Block this signal from emitting."""
        self._is_blocked = True

    def unblock(self) -> None:
        """Unblock this signal, allowing it to emit."""
        self._is_blocked = False

    @contextmanager
    def blocked(self) -> Iterator[None]:
        """Context manager to temporarly block this signal."""
        self.block()
        try:
            yield
        finally:
            self.unblock()


class EmitThread(threading.Thread):
    """A thread to emit a signal asynchronously."""

    def __init__(self, signal_instance: SignalInstance, args: Tuple[Any, ...]) -> None:
        super().__init__(name=signal_instance.name)
        self._signal_instance = signal_instance
        self.args = args
        # current = threading.currentThread()
        # self.parent = (current.getName(), current.ident)

    def run(self) -> None:
        """Run thread."""
        self._signal_instance._run_emit_loop(self.args)


# ################################################################


def _build_signature(*types: AnyType) -> Signature:
    params = [
        Parameter(name=f"p{i}", kind=Parameter.POSITIONAL_ONLY, annotation=t)
        for i, t in enumerate(types)
    ]
    return Signature(params)


# def f(a, /, b, c=None, *d, f=None, **g): print(locals())
#
# a: kind=POSITIONAL_ONLY,       default=Parameter.empty    # 1 required posarg
# b: kind=POSITIONAL_OR_KEYWORD, default=Parameter.empty    # 1 requires posarg
# c: kind=POSITIONAL_OR_KEYWORD, default=None               # 1 optional posarg
# d: kind=VAR_POSITIONAL,        default=Parameter.empty    # N optional posargs
# e: kind=KEYWORD_ONLY,          default=Parameter.empty    # 1 REQUIRED kwarg
# f: kind=KEYWORD_ONLY,          default=None               # 1 optional kwarg
# g: kind=VAR_KEYWORD,           default=Parameter.empty    # N optional kwargs


def _acceptable_posarg_range(
    sig: Signature, forbid_required_kwarg: bool = True
) -> Tuple[int, Optional[int]]:
    """Return tuple of (min, max) accepted positional arguments.

    Parameters
    ----------
    sig : Signature
        Signature object to evaluate
    forbid_required_kwarg : bool, optional
        Whether to allow required KEYWORD_ONLY parameters. by default True.

    Returns
    -------
    arg_range : Tuple[int, int]
        minimum, maximum number of acceptable positional arguments

    Raises
    ------
    ValueError
        If the signature has a required keyword_only parameter and
        `forbid_required_kwarg` is `True`.
    """
    required = 0
    optional = 0
    is_unbound = False
    for param in sig.parameters.values():
        if param.kind in {Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD}:
            if param.default is Parameter.empty:
                required += 1
            else:
                optional += 1
        elif param.kind is Parameter.VAR_POSITIONAL:
            is_unbound = True
        elif (
            param.kind is Parameter.KEYWORD_ONLY
            and param.default is Parameter.empty
            and forbid_required_kwarg
        ):
            raise ValueError("Required KEYWORD_ONLY parameters not allowed")
    return (required, None if is_unbound else required + optional)


def _parameter_types_match(
    function: Callable, spec: Signature, func_sig: Optional[Signature] = None
) -> bool:
    """Return True if types in `function` signature match those in `spec`.

    Parameters
    ----------
    function : Callable
        A function to validate
    spec : Signature
        The Signature against which the `function` should be validated.
    func_sig : Signature, optional
        Signature for `function`, if `None`, signature will be inspected.
        by default None

    Returns
    -------
    bool
        True if the parameter types match.
    """
    fsig = func_sig or signature(function)

    func_hints = None
    for f_param, spec_param in zip(fsig.parameters.values(), spec.parameters.values()):
        f_anno = f_param.annotation
        if f_anno is fsig.empty:
            # if function parameter is not type annotated, allow it.
            continue

        if isinstance(f_anno, str):
            if func_hints is None:
                from typing_extensions import get_type_hints

                func_hints = get_type_hints(function)
            f_anno = func_hints.get(f_param.name)

        if not _is_subclass(f_anno, spec_param.annotation):
            return False
    return True


def _is_subclass(left: AnyType, right: type) -> bool:
    from inspect import isclass

    from typing_extensions import get_args, get_origin

    if not isclass(left):
        # look for Union
        origin = get_origin(left)
        if origin is Union:
            return any(issubclass(i, right) for i in get_args(left))
    return issubclass(left, right)
