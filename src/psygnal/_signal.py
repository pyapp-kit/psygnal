from __future__ import annotations

import inspect
import threading
import warnings
import weakref
from contextlib import contextmanager, suppress
from functools import lru_cache, partial, reduce
from inspect import Parameter, Signature, isclass
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    ContextManager,
    Iterable,
    Iterator,
    NoReturn,
    Type,
    TypeVar,
    Union,
    cast,
    get_type_hints,
    overload,
)

from mypy_extensions import mypyc_attr
from typing_extensions import get_args, get_origin

from ._exceptions import EmitLoopError
from ._queue import QueuedCallback
from ._weak_callback import (
    StrongFunction,
    WeakCallback,
    WeakSetattr,
    WeakSetitem,
    weak_callback,
)

if TYPE_CHECKING:
    from typing_extensions import Literal

    from ._group import EmissionInfo
    from ._weak_callback import RefErrorChoice

    ReducerFunc = Callable[[tuple, tuple], tuple]

__all__ = ["Signal", "SignalInstance", "_compiled"]
_NULL = object()
F = TypeVar("F", bound=Callable)


class Signal:
    """Declares a signal emitter on a class.

    This is class implements the [descriptor
    protocol](https://docs.python.org/3/howto/descriptor.html#descriptorhowto)
    and is designed to be used as a class attribute, with the supported signature types
    provided in the constructor:

    ```python
    from psygnal import Signal

    class MyEmitter:
        changed = Signal(int)

    def receiver(arg: int):
        print("new value:", arg)

    emitter = MyEmitter()
    emitter.changed.connect(receiver)
    emitter.changed.emit(1)  # prints 'new value: 1'
    ```

    !!! note

        in the example above, `MyEmitter.changed` is an instance of `Signal`,
        and `emitter.changed` is an instance of `SignalInstance`.  See the
        documentation on [`SignalInstance`][psygnal.SignalInstance] for details
        on how to connect to and/or emit a signal on an instance of an object
        that has a `Signal`.


    Parameters
    ----------
    *types : Union[Type[Any], Signature]
        A sequence of individual types, or a *single* [`inspect.Signature`][] object.
    description : str
        Optional descriptive text for the signal.  (not used internally).
    name : Optional[str]
        Optional name of the signal. If it is not specified then the name of the
        class attribute that is bound to the signal will be used. default None
    check_nargs_on_connect : bool
        Whether to check the number of positional args against `signature` when
        connecting a new callback. This can also be provided at connection time using
        `.connect(..., check_nargs=True)`. By default, True.
    check_types_on_connect : bool
        Whether to check the callback parameter types against `signature` when
        connecting a new callback. This can also be provided at connection time using
        `.connect(..., check_types=True)`. By default, False.
    """

    # _signature: Signature  # callback signature for this signal

    _current_emitter: ClassVar[SignalInstance | None] = None

    def __init__(
        self,
        *types: type[Any] | Signature,
        description: str = "",
        name: str | None = None,
        check_nargs_on_connect: bool = True,
        check_types_on_connect: bool = False,
    ) -> None:
        self._name = name
        self.description = description
        self._check_nargs_on_connect = check_nargs_on_connect
        self._check_types_on_connect = check_types_on_connect
        self._signal_instance_class: type[SignalInstance] = SignalInstance

        if types and isinstance(types[0], Signature):
            self._signature = types[0]
            if len(types) > 1:
                warnings.warn(
                    "Only a single argument is accepted when directly providing a"
                    f" `Signature`.  These args were ignored: {types[1:]}",
                    stacklevel=2,
                )
        else:
            self._signature = _build_signature(*cast("tuple[Type[Any], ...]", types))

    @property
    def signature(self) -> Signature:
        """[Signature][inspect.Signature] supported by this Signal."""
        return self._signature

    def __set_name__(self, owner: type[Any], name: str) -> None:
        """Set name of signal when declared as a class attribute on `owner`."""
        if self._name is None:
            self._name = name

    @overload
    def __get__(
        self, instance: None, owner: type[Any] | None = None
    ) -> Signal: ...  # pragma: no cover

    @overload
    def __get__(
        self, instance: Any, owner: type[Any] | None = None
    ) -> SignalInstance: ...  # pragma: no cover

    def __get__(
        self, instance: Any, owner: type[Any] | None = None
    ) -> Signal | SignalInstance:
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
        name = cast("str", self._name)
        signal_instance = self._signal_instance_class(
            self.signature,
            instance=instance,
            name=name,
            check_nargs_on_connect=self._check_nargs_on_connect,
            check_types_on_connect=self._check_types_on_connect,
        )
        # instead of caching this signal instance on self, we just assign it
        # to instance.name ... this essentially breaks the descriptor,
        # (i.e. __get__ will never again be called for this instance, and we have no
        # idea how many instances are out there),
        # but it allows us to prevent creating a key for this instance (which may
        # not be hashable or weak-referenceable), and also provides a significant
        # speedup on attribute access (affecting everything).
        # (note, this is the same mechanism used in the `cached_property` decorator)
        try:
            setattr(instance, name, signal_instance)
        except AttributeError as e:
            from ._group import SignalGroup

            if name == "all" and isinstance(instance, SignalGroup):
                # this specific case will happen if an evented dataclass field is named
                # "all". 'all' is a reserved name for the SignalRelay, but we've
                # already caught and warned about it in SignalGroup.__init_subclass__.
                pass
            else:
                # otherwise, give an informative error message
                raise AttributeError(  # pragma: no cover
                    "An attempt to cache a SignalInstance on instance "
                    f"{instance} failed. Please report this with your use case at "
                    "https://github.com/pyapp-kit/psygnal/issues."
                ) from e

        return signal_instance

    @classmethod
    @contextmanager
    def _emitting(cls, emitter: SignalInstance) -> Iterator[None]:
        """Context that sets the sender on a receiver object while emitting a signal."""
        previous, cls._current_emitter = cls._current_emitter, emitter
        try:
            yield
        finally:
            cls._current_emitter = previous

    @classmethod
    def current_emitter(cls) -> SignalInstance | None:
        """Return currently emitting `SignalInstance`, if any.

        This will typically be used in a callback.

        Examples
        --------
        ```python
        from psygnal import Signal

        def my_callback():
            source = Signal.current_emitter()
        ```
        """
        return cls._current_emitter

    @classmethod
    def sender(cls) -> Any:
        """Return currently emitting object, if any.

        This will typically be used in a callback.
        """
        return getattr(cls._current_emitter, "instance", None)


_empty_signature = Signature()


@mypyc_attr(allow_interpreted_subclasses=True)
class SignalInstance:
    """A signal instance (optionally) bound to an object.

    In most cases, users will not create a `SignalInstance` directly -- instead
    creating a [Signal][psygnal.Signal] class attribute.  This object will be
    instantiated by the `Signal.__get__` method (i.e. the descriptor protocol),
    when a `Signal` instance is accessed from an *instance* of a class with `Signal`
    attribute.

    However, it is the `SignalInstance` that you will most often be interacting
    with when you access the name of a `Signal` on an instance -- so understanding
    the `SignalInstance` API is key to using psygnal.

    ```python
    class Emitter:
        signal = Signal()

    e = Emitter()

    # when accessed on an *instance* of Emitter,
    # the signal attribute will be a SignalInstance
    e.signal

    # This is what you will use to connect your callbacks
    e.signal.connect(some_callback)
    ```

    Parameters
    ----------
    signature : Optional[inspect.Signature]
        The signature that this signal accepts and will emit, by default `Signature()`.
    instance : Optional[Any]
        An object to which this signal is bound. Normally this will be provided by the
        `Signal.__get__` method (see above).  However, an unbound `SignalInstance`
        may also be created directly. by default `None`.
    name : Optional[str]
        An optional name for this signal.  Normally this will be provided by the
        `Signal.__get__` method. by default `None`
    check_nargs_on_connect : bool
        Whether to check the number of positional args against `signature` when
        connecting a new callback. This can also be provided at connection time using
        `.connect(..., check_nargs=True)`. By default, True.
    check_types_on_connect : bool
        Whether to check the callback parameter types against `signature` when
        connecting a new callback. This can also be provided at connection time using
        `.connect(..., check_types=True)`. By default, False.

    Raises
    ------
    TypeError
        If `signature` is neither an instance of `inspect.Signature`, or a `tuple`
        of types.
    """

    _is_blocked: bool = False
    _is_paused: bool = False
    _debug_hook: ClassVar[Callable[[EmissionInfo], None] | None] = None

    def __init__(
        self,
        signature: Signature | tuple = _empty_signature,
        *,
        instance: Any = None,
        name: str | None = None,
        check_nargs_on_connect: bool = True,
        check_types_on_connect: bool = False,
    ) -> None:
        self._name = name
        self._instance: Callable = self._instance_ref(instance)
        self._args_queue: list[Any] = []  # filled when paused

        if isinstance(signature, (list, tuple)):
            signature = _build_signature(*signature)
        elif not isinstance(signature, Signature):  # pragma: no cover
            raise TypeError(
                "`signature` must be either a sequence of types, or an "
                "instance of `inspect.Signature`"
            )

        self._signature = signature
        self._check_nargs_on_connect = check_nargs_on_connect
        self._check_types_on_connect = check_types_on_connect
        self._slots: list[WeakCallback] = []
        self._is_blocked: bool = False
        self._is_paused: bool = False
        self._lock = threading.RLock()

    @staticmethod
    def _instance_ref(instance: Any) -> Callable[[], Any]:
        if instance is None:
            return lambda: None

        try:
            return weakref.ref(instance)
        except TypeError:
            # fall back to strong reference if instance is not weak-referenceable
            return lambda: instance

    @property
    def signature(self) -> Signature:
        """Signature supported by this `SignalInstance`."""
        return self._signature

    @property
    def instance(self) -> Any:
        """Object that emits this `SignalInstance`."""
        return self._instance()

    @property
    def name(self) -> str:
        """Name of this `SignalInstance`."""
        return self._name or ""

    def __repr__(self) -> str:
        """Return repr."""
        name = f" {self._name!r}" if self._name else ""
        instance = f" on {self.instance!r}" if self.instance is not None else ""
        return f"<{type(self).__name__}{name}{instance}>"

    @overload
    def connect(
        self,
        *,
        thread: threading.Thread | Literal["main", "current"] | None = ...,
        check_nargs: bool | None = ...,
        check_types: bool | None = ...,
        unique: bool | str = ...,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = ...,
    ) -> Callable[[F], F]: ...  # pragma: no cover

    @overload
    def connect(
        self,
        slot: F,
        *,
        thread: threading.Thread | Literal["main", "current"] | None = ...,
        check_nargs: bool | None = ...,
        check_types: bool | None = ...,
        unique: bool | str = ...,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = ...,
    ) -> F: ...  # pragma: no cover

    def connect(
        self,
        slot: F | None = None,
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
    ) -> Callable[[F], F] | F:
        """Connect a callback (`slot`) to this signal.

        `slot` is compatible if:

        * it requires no more than the number of positional arguments emitted by this
          `SignalInstance`.  (It *may* require less)
        * it has no *required* keyword arguments (keyword only arguments that have
          no default).
        * if `check_types` is `True`, the parameter types in the callback signature must
          match the signature of this `SignalInstance`.

        This method may be used as a decorator.

        ```python
        @signal.connect
        def my_function():
            ...
        ```

        !!!important
            If a signal is connected with `thread != None`, then it is up to the user
            to ensure that `psygnal.emit_queued` is called, or that one of the backend
            convenience functions is used (e.g. `psygnal.qt.start_emitting_from_queue`).
            Otherwise, callbacks that are connected to signals that are emitted from
            another thread will never be called.

        Parameters
        ----------
        slot : Callable
            A callable to connect to this signal.  If the callable accepts less
            arguments than the signature of this slot, then they will be discarded when
            calling the slot.
        check_nargs : Optional[bool]
            If `True` and the provided `slot` requires more positional arguments than
            the signature of this Signal, raise `TypeError`. by default `True`.
        thread: Thread | Literal["main", "current"] | None
            If `None` (the default), this slot will be invoked immediately when a signal
            is emitted, from whatever thread emitted the signal. If a thread object is
            provided, then the callback will only be immediately invoked if the signal
            is emitted from that thread.  Otherwise, the callback will be added to a
            queue. **Note!**, when using the `thread` parameter, the user is responsible
            for calling `psygnal.emit_queued()` in the corresponding thread, otherwise
            the slot will never be invoked. (See note above). (The strings `"main"` and
            `"current"` are also accepted, and will be interpreted as the
            `threading.main_thread()` and `threading.current_thread()`, respectively).
        check_types : Optional[bool]
            If `True`, An additional check will be performed to make sure that types
            declared in the slot signature are compatible with the signature
            declared by this signal, by default `False`.
        unique : Union[bool, str, None]
            If `True`, returns without connecting if the slot has already been
            connected.  If the literal string "raise" is passed to `unique`, then a
            `ValueError` will be raised if the slot is already connected.
            By default `False`.
        max_args : Optional[int]
            If provided, `slot` will be called with no more more than `max_args` when
            this SignalInstance is emitted.  (regardless of how many arguments are
            emitted).
        on_ref_error : {'raise', 'warn', 'ignore'}, optional
            What to do if a weak reference cannot be created.  If 'raise', a
            ReferenceError will be raised.  If 'warn' (default), a warning will be
            issued and a strong-reference will be used. If 'ignore' a strong-reference
            will be used (silently).

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

        def _wrapper(
            slot: F,
            max_args: int | None = max_args,
            _on_ref_err: RefErrorChoice = on_ref_error,
        ) -> F:
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

                slot_sig: Signature | None = None
                if check_nargs and (max_args is None):
                    slot_sig, max_args, isqt = self._check_nargs(slot, self.signature)
                    if isqt:
                        _on_ref_err = "ignore"
                if check_types:
                    slot_sig = slot_sig or signature(slot)
                    if not _parameter_types_match(slot, self.signature, slot_sig):
                        extra = f"- Slot types {slot_sig} do not match types in signal."
                        self._raise_connection_error(slot, extra)

                cb = weak_callback(
                    slot,
                    max_args=max_args,
                    finalize=self._try_discard,
                    on_ref_error=_on_ref_err,
                )
                if thread is None:
                    self._slots.append(cb)
                else:
                    self._slots.append(QueuedCallback(cb, thread=thread))
            return slot

        return _wrapper if slot is None else _wrapper(slot)

    def _try_discard(self, callback: WeakCallback, missing_ok: bool = True) -> None:
        """Try to discard a callback from the list of slots.

        Parameters
        ----------
        callback : WeakCallback
            A callback to discard.
        missing_ok : bool, optional
            If `True`, do not raise an error if the callback is not found in the list.
        """
        try:
            self._slots.remove(callback)
        except ValueError:
            if not missing_ok:
                raise

    def connect_setattr(
        self,
        obj: weakref.ref | object,
        attr: str,
        maxargs: int | None | object = _NULL,
        *,
        on_ref_error: RefErrorChoice = "warn",
    ) -> WeakCallback[None]:
        """Bind an object attribute to the emitted value of this signal.

        Equivalent to calling `self.connect(functools.partial(setattr, obj, attr))`,
        but with additional weakref safety (i.e. a strong reference to `obj` will not
        be retained). The return object can be used to
        [`disconnect()`][psygnal.SignalInstance.disconnect], (or you can use
        [`disconnect_setattr()`][psygnal.SignalInstance.disconnect_setattr]).

        Parameters
        ----------
        obj : Union[weakref.ref, object]
            An object or weak reference (deprecated) to an object.
        attr : str
            The name of an attribute on `obj` that should be set to the value of this
            signal when emitted.
        maxargs : Optional[int]
            max number of positional args to accept
        on_ref_error: {'raise', 'warn', 'ignore'}, optional
            What to do if a weak reference cannot be created.  If 'raise', a
            ReferenceError will be raised.  If 'warn' (default), a warning will be
            issued and a strong-reference will be used. If 'ignore' a strong-reference
            will be used (silently).

        Returns
        -------
        Tuple
            (weakref.ref, name, callable).  Reference to the object, name of the
            attribute, and setattr closure.  Can be used to disconnect the slot.

        Raises
        ------
        ValueError
            If this is not a single-value signal
        AttributeError
            If `obj` has no attribute `attr`.

        Examples
        --------
        >>> class T:
        ...     sig = Signal(int)
        ...
        >>> class SomeObj:
        ...     x = 1
        ...
        >>> t = T()
        >>> my_obj = SomeObj()
        >>> t.sig.connect_setattr(my_obj, 'x')
        >>> t.sig.emit(5)
        >>> assert my_obj.x == 5
        """
        if maxargs is _NULL:
            warnings.warn(
                "The default value of maxargs will change from `None` to `1` in"
                "version 0.11. To silence this warning, provide an explicit value for "
                "maxargs (`None` for current behavior, `1` for future behavior).",
                FutureWarning,
                stacklevel=2,
            )
            maxargs = None

        if isinstance(obj, weakref.ReferenceType):  # pragma: no cover
            warnings.warn(
                'Using a weakref as the "obj" argument is deprecated. '
                "Use the object directly instead. This will raise an error in "
                "a future release.",
                FutureWarning,
                stacklevel=2,
            )
            obj = obj()
        if not hasattr(obj, attr):
            raise AttributeError(f"Object {obj} has no attribute {attr!r}")

        with self._lock:
            caller = WeakSetattr(
                obj,
                attr,
                max_args=cast("int | None", maxargs),
                finalize=self._try_discard,
                on_ref_error=on_ref_error,
            )
            self._slots.append(caller)
        return caller

    def disconnect_setattr(
        self, obj: object, attr: str, missing_ok: bool = True
    ) -> None:
        """Disconnect a previously connected attribute setter.

        Parameters
        ----------
        obj : object
            An object.
        attr : str
            The name of an attribute on `obj` that was previously used for
            `connect_setattr`.
        missing_ok : bool
            If `False` and the provided `slot` is not connected, raises `ValueError`.
            by default `True`

        Raises
        ------
        ValueError
            If `missing_ok` is `True` and no attribute setter is connected.
        """
        # sourcery skip: merge-nested-ifs, use-next
        with self._lock:
            cb = WeakSetattr(obj, attr, on_ref_error="ignore")
            self._try_discard(cb, missing_ok)

    def connect_setitem(
        self,
        obj: weakref.ref | object,
        key: str,
        maxargs: int | None | object = _NULL,
        *,
        on_ref_error: RefErrorChoice = "warn",
    ) -> WeakCallback[None]:
        """Bind a container item (such as a dict key) to emitted value of this signal.

        Equivalent to calling `self.connect(functools.partial(obj.__setitem__, attr))`,
        but with additional weakref safety (i.e. a strong reference to `obj` will not
        be retained). The return object can be used to
        [`disconnect()`][psygnal.SignalInstance.disconnect], (or you can use
        [`disconnect_setitem()`][psygnal.SignalInstance.disconnect_setitem]).

        Parameters
        ----------
        obj : Union[weakref.ref, object]
            An object or weak reference (deprecated) to an object.
        key : str
            Name of the key in `obj` that should be set to the value of this
            signal when emitted
        maxargs : Optional[int]
            max number of positional args to accept
        on_ref_error: {'raise', 'warn', 'ignore'}, optional
            What to do if a weak reference cannot be created.  If 'raise', a
            ReferenceError will be raised.  If 'warn' (default), a warning will be
            issued and a strong-reference will be used. If 'ignore' a strong-reference
            will be used (silently).

        Returns
        -------
        Tuple
            (weakref.ref, name, callable).  Reference to the object, name of the
            attribute, and setitem closure.  Can be used to disconnect the slot.

        Raises
        ------
        ValueError
            If this is not a single-value signal
        TypeError
            If `obj` does not support __setitem__.

        Examples
        --------
        >>> class T:
        ...     sig = Signal(int)
        ...
        >>> t = T()
        >>> my_obj = dict()
        >>> t.sig.connect_setitem(my_obj, 'x')
        >>> t.sig.emit(5)
        >>> assert my_obj == {'x': 5}
        """
        if maxargs is _NULL:
            warnings.warn(
                "The default value of maxargs will change from `None` to `1` in"
                "version 0.11. To silence this warning, provide an explicit value for "
                "maxargs (`None` for current behavior, `1` for future behavior).",
                FutureWarning,
                stacklevel=2,
            )
            maxargs = None

        if isinstance(obj, weakref.ReferenceType):  # pragma: no cover
            warnings.warn(
                'Using a weakref as the "obj" argument is deprecated. '
                "Use the object directly instead. This will raise an error in "
                "a future release.",
                FutureWarning,
                stacklevel=2,
            )
            obj = obj()
        if not hasattr(obj, "__setitem__"):
            raise TypeError(f"Object {obj} does not support __setitem__")

        with self._lock:
            caller = WeakSetitem(
                obj,  # type: ignore
                key,
                max_args=cast("int | None", maxargs),
                finalize=self._try_discard,
                on_ref_error=on_ref_error,
            )
            self._slots.append(caller)

        return caller

    def disconnect_setitem(
        self, obj: object, key: str, missing_ok: bool = True
    ) -> None:
        """Disconnect a previously connected item setter.

        Parameters
        ----------
        obj : object
            An object.
        key : str
            The name of a key in `obj` that was previously used for
            `connect_setitem`.
        missing_ok : bool
            If `False` and the provided `slot` is not connected, raises `ValueError`.
            by default `True`

        Raises
        ------
        ValueError
            If `missing_ok` is `True` and no item setter is connected.
        """
        if not hasattr(obj, "__setitem__"):
            raise TypeError(f"Object {obj} does not support __setitem__")

        # sourcery skip: merge-nested-ifs, use-next
        with self._lock:
            caller = WeakSetitem(obj, key, on_ref_error="ignore")
            self._try_discard(caller, missing_ok)

    def _check_nargs(
        self, slot: Callable, spec: Signature
    ) -> tuple[Signature | None, int | None, bool]:
        """Make sure slot is compatible with signature.

        Also returns the maximum number of arguments that we can pass to the slot

        Returns
        -------
        slot_sig : Signature | None
            The signature of the slot, or None if it could not be determined.
        maxargs : int | None
            The maximum number of arguments that we can pass to the slot.
        is_qt : bool
            Whether the slot is a Qt slot.
        """
        try:
            slot_sig = _get_signature_possibly_qt(slot)
        except ValueError as e:
            warnings.warn(
                f"{e}. To silence this warning, connect with " "`check_nargs=False`",
                stacklevel=2,
            )
            return None, None, False
        try:
            minargs, maxargs = _acceptable_posarg_range(slot_sig)
        except ValueError as e:
            if isinstance(slot, partial):
                raise ValueError(
                    f"{e}. (Note: prefer using positional args with "
                    "functools.partials when possible)."
                ) from e
            raise

        # if `slot` requires more arguments than we will provide, raise.
        if minargs > (n_spec_params := len(spec.parameters)):
            extra = (
                f"- Slot requires at least {minargs} positional "
                f"arguments, but spec only provides {n_spec_params}"
            )
            self._raise_connection_error(slot, extra)

        return None if isinstance(slot_sig, str) else slot_sig, maxargs, True

    def _raise_connection_error(self, slot: Callable, extra: str = "") -> NoReturn:
        name = getattr(slot, "__name__", str(slot))
        msg = f"Cannot connect slot {name!r} with signature: {signature(slot)}:\n"
        msg += extra
        msg += f"\n\nAccepted signature: {self.signature}"
        raise ValueError(msg)

    def _slot_index(self, slot: Callable) -> int:
        """Get index of `slot` in `self._slots`.  Return -1 if not connected."""
        with self._lock:
            normed = weak_callback(slot, on_ref_error="ignore")
            # NOTE:
            # the == method here relies on the __eq__ method of each SlotCaller subclass
            return next((i for i, s in enumerate(self._slots) if s == normed), -1)

    def disconnect(self, slot: Callable | None = None, missing_ok: bool = True) -> None:
        """Disconnect slot from signal.

        Parameters
        ----------
        slot : callable, optional
            The specific slot to disconnect.  If `None`, all slots will be disconnected,
            by default `None`
        missing_ok : Optional[bool]
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

    def __contains__(self, slot: Callable) -> bool:
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
    ) -> None: ...  # pragma: no cover

    @overload
    def emit(
        self,
        *args: Any,
        check_nargs: bool = False,
        check_types: bool = False,
        asynchronous: Literal[True],
    ) -> EmitThread | None:
        # will return `None` if emitter is blocked
        ...  # pragma: no cover

    def emit(
        self,
        *args: Any,
        check_nargs: bool = False,
        check_types: bool = False,
        asynchronous: bool = False,
    ) -> EmitThread | None:
        """Emit this signal with arguments `args`.

        !!! note

            `check_args` and `check_types` both add overhead when calling emit.

        Parameters
        ----------
        *args : Any
            These arguments will be passed when calling each slot (unless the slot
            accepts fewer arguments, in which case extra args will be discarded.)
        check_nargs : bool
            If `False` and the provided arguments cannot be successfully bound to the
            signature of this Signal, raise `TypeError`.  Incurs some overhead.
            by default False.
        check_types : bool
            If `False` and the provided arguments do not match the types declared by
            the signature of this Signal, raise `TypeError`.  Incurs some overhead.
            by default False.
        asynchronous : bool
            If `True`, run signal emission in another thread. by default `False`.
            **DEPRECATED:**. *If you need to emit from a thread, please just create
            your own [`threading.Thread`][] and call
            [`SignalInstance.emit`][psygnal.SignalInstance.emit]. See also the `thread`
            parameter in the [`SignalInstance.connect`][psygnal.SignalInstance.connect]
            method.*

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
                ) from e

        if check_types and not _parameter_types_match(
            lambda: None, self.signature, _build_signature(*[type(a) for a in args])
        ):
            raise TypeError(
                f"Types provided to '{self.name}.emit' "
                f"{tuple(type(a).__name__ for a in args)} do not match signal "
                f"signature: {self.signature}"
            )

        if self._is_paused:
            self._args_queue.append(args)
            return None

        if SignalInstance._debug_hook is not None:
            from ._group import EmissionInfo

            SignalInstance._debug_hook(EmissionInfo(self, args))

        if asynchronous:
            warnings.warn(
                "The `asynchronous` parameter is deprecated and will be removed in a "
                "future release. If you need this, please create your own "
                "`threading.Thread` and call `SignalInstance.emit`. See also the new "
                "`thread` parameter in the `SignalInstance.connect` method.",
                FutureWarning,
                stacklevel=2,
            )
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
    ) -> None: ...  # pragma: no cover

    @overload
    def __call__(
        self,
        *args: Any,
        check_nargs: bool = False,
        check_types: bool = False,
        asynchronous: Literal[True],
    ) -> EmitThread | None:
        # will return `None` if emitter is blocked
        ...  # pragma: no cover

    def __call__(
        self,
        *args: Any,
        check_nargs: bool = False,
        check_types: bool = False,
        asynchronous: bool = False,
    ) -> EmitThread | None:
        """Alias for `emit()`."""
        return self.emit(  # type: ignore
            *args,
            check_nargs=check_nargs,
            check_types=check_types,
            asynchronous=asynchronous,
        )

    def _run_emit_loop(self, args: tuple[Any, ...]) -> None:
        # allow receiver to query sender with Signal.current_emitter()
        with self._lock:
            with Signal._emitting(self):
                for caller in self._slots:
                    try:
                        caller.cb(args)
                    except Exception as e:
                        raise EmitLoopError(
                            cb=caller, args=args, exc=e, signal=self
                        ) from e

        return None

    def block(self, exclude: Iterable[str | SignalInstance] = ()) -> None:
        """Block this signal from emitting.

        NOTE: the `exclude` argument is only for SignalGroup subclass, but we
        have to include it here to make mypyc happy.
        """
        self._is_blocked = True

    def unblock(self) -> None:
        """Unblock this signal, allowing it to emit."""
        self._is_blocked = False

    def blocked(self) -> ContextManager[None]:
        """Context manager to temporarily block this signal.

        Useful if you need to temporarily block all emission of a given signal,
        (for example, to avoid a recursive signal loop)

        Examples
        --------
        ```python
        class MyEmitter:
            changed = Signal()

            def make_a_change(self):
                self.changed.emit()

        obj = MyEmitter()

        with obj.changed.blocked()
            obj.make_a_change()  # will NOT emit a changed signal.
        ```
        """
        return _SignalBlocker(self)

    def pause(self) -> None:
        """Pause all emission and collect *args tuples from emit().

        args passed to `emit` will be collected and re-emitted when `resume()` is
        called. For a context manager version, see `paused()`.
        """
        self._is_paused = True

    def resume(self, reducer: ReducerFunc | None = None, initial: Any = _NULL) -> None:
        """Resume (unpause) this signal, emitting everything in the queue.

        Parameters
        ----------
        reducer : Callable[[tuple, tuple], Any], optional
            If provided, all gathered args will be reduced into a single argument by
            passing `reducer` to `functools.reduce`.
            NOTE: args passed to `emit` are collected as tuples, so the two arguments
            passed to `reducer` will always be tuples. `reducer` must handle that and
            return an args tuple.
            For example, three `emit(1)` events would be reduced and re-emitted as
            follows: `self.emit(*functools.reduce(reducer, [(1,), (1,), (1,)]))`

        initial: any, optional
            initial value to pass to `functools.reduce`

        Examples
        --------
        >>> class T:
        ...     sig = Signal(int)
        >>> t = T()
        >>> t.sig.pause()
        >>> t.sig.emit(1)
        >>> t.sig.emit(2)
        >>> t.sig.emit(3)
        >>> t.sig.resume(lambda a, b: (a[0].union(set(b)),), (set(),))
        >>> # results in t.sig.emit({1, 2, 3})
        """
        self._is_paused = False
        # not sure why this attribute wouldn't be set, but when resuming in
        # EventedModel.update, it may be undefined (as seen in tests)
        if not getattr(self, "_args_queue", None):
            return
        if reducer is not None:
            if initial is _NULL:
                args = reduce(reducer, self._args_queue)
            else:
                args = reduce(reducer, self._args_queue, initial)
            self._run_emit_loop(args)
        else:
            for args in self._args_queue:
                self._run_emit_loop(args)
        self._args_queue.clear()

    def paused(
        self, reducer: ReducerFunc | None = None, initial: Any = _NULL
    ) -> ContextManager[None]:
        """Context manager to temporarily pause this signal.

        Parameters
        ----------
        reducer : Callable[[tuple, tuple], Any], optional
            If provided, all gathered args will be reduced into a single argument by
            passing `reducer` to `functools.reduce`.
            NOTE: args passed to `emit` are collected as tuples, so the two arguments
            passed to `reducer` will always be tuples. `reducer` must handle that and
            return an args tuple.
            For example, three `emit(1)` events would be reduced and re-emitted as
            follows: `self.emit(*functools.reduce(reducer, [(1,), (1,), (1,)]))`
        initial: any, optional
            initial value to pass to `functools.reduce`

        Examples
        --------
        >>> with obj.signal.paused(lambda a, b: (a[0].union(set(b)),), (set(),)):
        ...     t.sig.emit(1)
        ...     t.sig.emit(2)
        ...     t.sig.emit(3)
        >>> # results in obj.signal.emit({1, 2, 3})
        """
        return _SignalPauser(self, reducer, initial)

    def __getstate__(self) -> dict:
        """Return dict of current state, for pickle."""
        attrs = (
            "_signature",
            "_name",
            "_is_blocked",
            "_is_paused",
            "_args_queue",
            "_check_nargs_on_connect",
            "_check_types_on_connect",
        )
        dd = {slot: getattr(self, slot) for slot in attrs}
        dd["_instance"] = self._instance()
        dd["_slots"] = [x for x in self._slots if isinstance(x, StrongFunction)]
        if len(self._slots) > len(dd["_slots"]):
            warnings.warn(
                "Pickling a SignalInstance does not copy connected weakly referenced "
                "slots.",
                stacklevel=2,
            )

        return dd

    def __setstate__(self, state: dict) -> None:
        """Restore state from pickle."""
        # don't use __dict__, mypyc doesn't have it
        for k, v in state.items():
            if k == "_instance":
                self._instance = self._instance_ref(v)
            else:
                setattr(self, k, v)
        self._lock = threading.RLock()


class _SignalBlocker:
    """Context manager to block and unblock a signal."""

    def __init__(
        self, signal: SignalInstance, exclude: Iterable[str | SignalInstance] = ()
    ) -> None:
        self._signal = signal
        self._exclude = exclude
        self._was_blocked = signal._is_blocked

    def __enter__(self) -> None:
        self._signal.block(exclude=self._exclude)

    def __exit__(self, *args: Any) -> None:
        if not self._was_blocked:
            self._signal.unblock()


class _SignalPauser:
    """Context manager to pause and resume a signal."""

    def __init__(
        self, signal: SignalInstance, reducer: ReducerFunc | None, initial: Any
    ) -> None:
        self._was_paused = signal._is_paused
        self._signal = signal
        self._reducer = reducer
        self._initial = initial

    def __enter__(self) -> None:
        self._signal.pause()

    def __exit__(self, *args: Any) -> None:
        if not self._was_paused:
            self._signal.resume(self._reducer, self._initial)


class EmitThread(threading.Thread):
    """A thread to emit a signal asynchronously."""

    def __init__(self, signal_instance: SignalInstance, args: tuple[Any, ...]) -> None:
        super().__init__(name=signal_instance.name)
        self._signal_instance = signal_instance
        self.args = args
        # current = threading.currentThread()
        # self.parent = (current.getName(), current.ident)

    def run(self) -> None:
        """Run thread."""
        self._signal_instance._run_emit_loop(self.args)


# #############################################################################
# #############################################################################


def signature(obj: Any) -> inspect.Signature:
    try:
        return inspect.signature(obj)
    except ValueError as e:
        with suppress(Exception):
            if not inspect.ismethod(obj):
                return _stub_sig(obj)
        raise e from e


_ANYSIG = Signature(
    [
        Parameter(name="args", kind=Parameter.VAR_POSITIONAL),
        Parameter(name="kwargs", kind=Parameter.VAR_KEYWORD),
    ]
)


@lru_cache(maxsize=None)
def _stub_sig(obj: Any) -> Signature:
    """Called as a backup when inspect.signature fails."""
    import builtins

    # this nonsense is here because it's hard to get the signature of mypyc-compiled
    # objects, but we still want to be able to connect a signal instance.
    if (
        type(getattr(obj, "__self__", None)) is SignalInstance
        and getattr(obj, "__name__", None) == "emit"
    ) or type(obj) is SignalInstance:
        # we won't reach this in testing because
        # Compiled functions don't trigger profiling and tracing hooks
        return _ANYSIG  # pragma: no cover

    # just a common case
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


def _build_signature(*types: type[Any]) -> Signature:
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


def _get_signature_possibly_qt(slot: Callable) -> Signature | str:
    # checking qt has to come first, since the signature of the emit method
    # of a Qt SignalInstance is just <Signature (*args: typing.Any) -> None>
    # https://bugreports.qt.io/browse/PYSIDE-1713
    sig = _guess_qtsignal_signature(slot)
    return signature(slot) if sig is None else sig


def _acceptable_posarg_range(
    sig: Signature | str, forbid_required_kwarg: bool = True
) -> tuple[int, int | None]:
    """Return tuple of (min, max) accepted positional arguments.

    Parameters
    ----------
    sig : Signature
        Signature object to evaluate
    forbid_required_kwarg : Optional[bool]
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
    if isinstance(sig, str):
        if "(" not in sig:  # pragma: no cover
            raise ValueError(f"Unrecognized string signature format: {sig!r}")
        inner = sig.split("(", 1)[1].split(")", 1)[0]
        minargs = maxargs = inner.count(",") + 1 if inner else 0
        return minargs, maxargs

    required = 0
    optional = 0
    posargs_unlimited = False
    _pos_required = {Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD}
    for param in sig.parameters.values():
        if param.kind in _pos_required:
            if param.default is Parameter.empty:
                required += 1
            else:
                optional += 1
        elif param.kind is Parameter.VAR_POSITIONAL:
            posargs_unlimited = True
        elif (
            param.kind is Parameter.KEYWORD_ONLY
            and param.default is Parameter.empty
            and forbid_required_kwarg
        ):
            raise ValueError(f"Unsupported KEYWORD_ONLY parameters in signature: {sig}")
    return (required, None if posargs_unlimited else required + optional)


def _parameter_types_match(
    function: Callable, spec: Signature, func_sig: Signature | None = None
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

    func_hints: dict | None = None
    for f_param, spec_param in zip(fsig.parameters.values(), spec.parameters.values()):
        f_anno = f_param.annotation
        if f_anno is fsig.empty:
            # if function parameter is not type annotated, allow it.
            continue

        if isinstance(f_anno, str):
            if func_hints is None:
                func_hints = get_type_hints(function)
            f_anno = func_hints.get(f_param.name)

        if not _is_subclass(f_anno, spec_param.annotation):
            return False
    return True


def _is_subclass(left: type[Any], right: type) -> bool:
    """Variant of issubclass with support for unions."""
    if not isclass(left) and get_origin(left) is Union:
        return any(issubclass(i, right) for i in get_args(left))
    return issubclass(left, right)


def _guess_qtsignal_signature(obj: Any) -> str | None:
    """Return string signature if `obj` is a SignalInstance or Qt emit method.

    This is a bit of a hack, but we found no better way:
    https://stackoverflow.com/q/69976089/1631624
    https://bugreports.qt.io/browse/PYSIDE-1713
    """
    # on my machine, this takes ~700ns on PyQt5 and 8.7µs on PySide2
    type_ = type(obj)
    if "pyqtBoundSignal" in type_.__name__:
        return cast("str", obj.signal)
    qualname = getattr(obj, "__qualname__", "")
    if qualname == "pyqtBoundSignal.emit":
        return cast("str", obj.__self__.signal)

    # note: this IS all actually covered in tests... but only in the Qt tests,
    # so it (annoyingly) briefly looks like it fails coverage.
    if qualname == "SignalInstance.emit" and type_.__name__.startswith("builtin"):
        # we likely have the emit method of a SignalInstance
        # call it with ridiculous params to get the err
        return _ridiculously_call_emit(obj.__self__.emit)  # pragma: no cover
    if "SignalInstance" in type_.__name__ and "QtCore" in getattr(
        type_, "__module__", ""
    ):  # pragma: no cover
        return _ridiculously_call_emit(obj.emit)
    return None


_CRAZY_ARGS = (1,) * 255


# note: this IS all actually covered in tests... but only in the Qt tests,
# so it (annoyingly) briefly looks like it fails coverage.
def _ridiculously_call_emit(emitter: Any) -> str | None:  # pragma: no cover
    """Call SignalInstance emit() to get the signature from err message."""
    try:
        emitter(*_CRAZY_ARGS)
    except TypeError as e:
        if "only accepts" in str(e):
            return str(e).split("only accepts")[0].strip()
    return None  # pragma: no cover


_compiled: bool


def __getattr__(name: str) -> Any:
    if name == "_compiled":
        return hasattr(Signal, "__mypyc_attrs__")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
