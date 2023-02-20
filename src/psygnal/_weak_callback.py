from __future__ import annotations

import weakref
from functools import partial
from types import BuiltinMethodType, FunctionType, MethodType, MethodWrapperType
from typing import TYPE_CHECKING, Any, Callable, TypeVar, cast
from warnings import warn

from typing_extensions import Protocol

if TYPE_CHECKING:
    from typing_extensions import Literal, TypeAlias

    RefErrorChoice: TypeAlias = Literal["raise", "warn", "ignore"]

__all__ = ["weak_callback", "WeakCallback"]
_T = TypeVar("_T")


class Q:
    __slots__ = ("__weakref__",)


def weak_callback(
    cb: Callable | WeakCallback,
    *args: Any,
    max_args: int | None = None,
    finalize: Callable[[WeakCallback], Any] | None = None,
    strong_func: bool = True,
    on_ref_error: RefErrorChoice = "warn",
) -> WeakCallback:
    """Create a weakly-referenced callback.

    This function creates a weakly-referenced callback, with special considerations
    for many known callable types (functions, lambdas, partials, bound methods,
    partials on bound methods, builtin methods, etc.).

    NOTE: For the sake of least-surprise, an exception is made for functions and,
    lambdas, which are strongly-referenced by default.  See the `strong_func` parameter
    for more details.

    Parameters
    ----------
    cb : callable
        The callable to be called.
    *args
        Additional positional arguments to be passed to the callback (similar
        to functools.partial).
    max_args : int, optional
        The maximum number of positional arguments to pass to the callback.
        If provided, additional arguments passed to WeakCallback.cb will be ignored.
    finalize : callable, optional
        A callable that will be called when the callback is garbage collected.
        The callable will be passed the WeakCallback instance as its only argument.
    strong_func : bool, optional
        If True (default), a strong reference will be kept to the function `cb` if
        it is a function or lambda.  If False, a weak reference will be kept.  The
        reasoning for the is that functions and lambdas are so often defined *only*
        to be passed to this function, and will likely be immediately garbage
        collected.  If you would specifically like to *allow* the function to be
        garbage collected, set this to False.
    on_ref_error : {'raise', 'warn', 'ignore'}, optional
        What to do if a weak reference cannot be created.  If 'raise', a
        ReferenceError will be raised.  If 'warn' (default), a warning will be issued
        and a strong-reference will be used. If 'ignore' a strong-reference will be
        used (silently).

    Returns
    -------
    WeakCallback
        A WeakCallback subclass instance appropriate for the given callable.

    Examples
    --------
    ```python
        from psygnal._weak_callback import weak_callback

    class T:
        def greet(self, name):
            print("hello,", name)

    def _on_delete(weak_cb):
        print("deleting!")

    t = T()
    weak_cb = weak_callback(t.greet, finalize=_on_delete)

    weak_cb.cb(("world",))  # "hello, world"

    del t  # "deleting!"

    weak_cb.cb(("world",))  # ReferenceError
    ```
    """
    if isinstance(cb, WeakCallback):
        return cb

    kwargs = None
    if isinstance(cb, partial):
        args = cb.args + args
        kwargs = cb.keywords
        cb = cb.func

    if isinstance(cb, FunctionType):
        return (
            _StrongFunction(cb, max_args, args, kwargs)
            if strong_func
            else _WeakFunction(cb, max_args, args, kwargs, finalize, on_ref_error)
        )

    if isinstance(cb, MethodType):
        if getattr(cb, "__name__", None) == "__setitem__":
            try:
                key = args[0]
            except IndexError as e:  # pragma: no cover
                raise TypeError(
                    "WeakCallback.__setitem__ requires a key argument"
                ) from e
            obj = cast("SupportsSetitem", cb.__self__)
            return _WeakSetitem(obj, key, max_args, finalize, on_ref_error)
        return _WeakMethod(cb, max_args, args, kwargs, finalize, on_ref_error)

    if isinstance(cb, (MethodWrapperType, BuiltinMethodType)):
        if cb is setattr:
            try:
                obj, attr = args[:2]
            except IndexError as e:  # pragma: no cover
                raise TypeError(
                    "setattr requires two arguments, an object and an attribute name."
                ) from e
            return _WeakSetattr(obj, attr, max_args, finalize, on_ref_error)
        return _WeakBuiltin(cb, max_args, finalize, on_ref_error)

    if callable(cb):
        return _WeakFunction(cb, max_args, args, kwargs, finalize, on_ref_error)

    raise TypeError(f"unsupported type {type(cb)}")  # pragma: no cover


class SupportsSetitem(Protocol):
    def __setitem__(self, key: Any, value: Any) -> None:
        ...


class WeakCallback:
    """Abstract Base Class for weakly-referenced callbacks.

    Do not instantiate this class directly, use the `weak_callback` function instead.

    NOTE: can't use ABC here because then mypyc and PySide2 don't play nice together.
    """

    def __init__(
        self,
        obj: Any,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
    ) -> None:
        self._key = WeakCallback.object_key(obj)
        self._max_args = max_args
        self._alive = True
        self._on_ref_error = on_ref_error

    def cb(self, args: tuple[Any, ...] = ()) -> None:
        """Call the callback with `args`. Args will be spread when calling the func."""
        raise NotImplementedError()

    def dereference(self) -> object | None:
        """Return the original object, or None if dead."""
        raise NotImplementedError()

    def __eq__(self, other: object) -> bool:
        # sourcery skip: swap-if-expression
        if isinstance(other, WeakCallback):
            return self._key == other._key
        return NotImplemented

    def _try_ref(
        self,
        obj: _T,
        finalize: Callable[[WeakCallback], Any] | None = None,
    ) -> Callable[[], _T | None]:
        _cb = None if finalize is None else _kill_and_finalize(self, finalize)
        try:
            return weakref.ref(obj, _cb)
        except TypeError:
            if self._on_ref_error == "raise":
                raise
            if self._on_ref_error == "warn":
                # FIXME: special case (move me)
                mod = getattr(obj, "__module__", None) or ""
                if "QtCore" not in mod:
                    warn(f"failed to create weakref for {obj!r}, returning strong ref")

            def _strong_ref() -> _T:
                return obj

            return _strong_ref

    @staticmethod
    def object_key(obj: Any) -> str:
        if hasattr(obj, "__self__"):
            owner_cls = type(obj.__self__)
            type_name = getattr(owner_cls, "__name__", None) or ""
            module = getattr(owner_cls, "__module__", None) or ""
            method_name = getattr(obj, "__name__", None) or ""
            obj_name = f"{type_name}.{method_name}"
            obj_id = id(obj.__self__)
        else:
            module = getattr(obj, "__module__", None) or ""
            obj_name = getattr(obj, "__name__", None) or ""
            obj_id = id(obj)
        return f"{module}:{obj_name}@{hex(obj_id)}"


def _kill_and_finalize(
    wcb: WeakCallback, finalize: Callable[[WeakCallback], Any]
) -> Callable[[weakref.ReferenceType], None]:
    def _cb(_: weakref.ReferenceType) -> None:
        if wcb._alive:
            wcb._alive = False
            finalize(wcb)

    return _cb


class _StrongFunction(WeakCallback):
    def __init__(
        self,
        f: Callable,
        max_args: int | None = None,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        on_ref_error: RefErrorChoice = "warn",
    ) -> None:
        super().__init__(f, max_args, on_ref_error)
        self._f = f
        self._args = args
        self._kwargs = kwargs or {}

    def cb(self, args: tuple[Any, ...] = ()) -> None:
        if self._max_args is None:
            if self._kwargs:
                self._f(*self._args, *args, **self._kwargs)
            else:
                self._f(*self._args, *args)
        elif self._kwargs:
            self._f(*self._args, *args[: self._max_args], **self._kwargs)
        else:
            self._f(*self._args, *args[: self._max_args])

    def dereference(self) -> Callable:
        if self._args or self._kwargs:
            return partial(self._f, *self._args, **self._kwargs)
        return self._f


class _WeakFunction(WeakCallback):
    def __init__(
        self,
        f: Callable,
        max_args: int | None = None,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        finalize: Callable | None = None,
        on_ref_error: RefErrorChoice = "warn",
    ) -> None:
        super().__init__(f, max_args, on_ref_error)
        self._f = self._try_ref(f, finalize)
        self._args = args
        self._kwargs = kwargs or {}

    def cb(self, args: tuple[Any, ...] = ()) -> None:
        f = self._f()
        if f is None:
            raise ReferenceError("weakly-referenced object no longer exists")
        if self._max_args is None:
            if self._kwargs:
                f(*self._args, *args, **self._kwargs)
            else:
                f(*self._args, *args)
        elif self._kwargs:
            f(*self._args, *args[: self._max_args], **self._kwargs)
        else:
            f(*self._args, *args[: self._max_args])

    def dereference(self) -> Callable | None:
        f = self._f()
        if f is None:
            return None
        if self._args or self._kwargs:
            return partial(f, *self._args, **self._kwargs)
        return f


class _WeakMethod(WeakCallback):
    def __init__(
        self,
        f: MethodType,
        max_args: int | None = None,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        finalize: Callable | None = None,
        on_ref_error: RefErrorChoice = "warn",
    ) -> None:
        super().__init__(f.__self__, max_args, on_ref_error)
        self._obj_ref = self._try_ref(f.__self__, finalize)
        self._func_ref = self._try_ref(f.__func__, finalize)
        self._args = args
        self._kwargs = kwargs or {}

    def cb(self, args: tuple[Any, ...] = ()) -> None:
        obj = self._obj_ref()
        func = self._func_ref()
        if obj is None or func is None:
            raise ReferenceError("weakly-referenced object no longer exists")
        if self._max_args is None:
            if self._kwargs:
                func(obj, *self._args, *args, **self._kwargs)
            else:
                func(obj, *self._args, *args)
        elif self._kwargs:
            func(obj, *self._args, *args[: self._max_args], **self._kwargs)
        else:
            func(obj, *self._args, *args[: self._max_args])

    def dereference(self) -> MethodType | partial | None:
        obj = self._obj_ref()
        func = self._func_ref()
        if obj is None or func is None:
            return None
        method = func.__get__(obj)
        if self._args or self._kwargs:
            return partial(method, *self._args, **self._kwargs)
        return method


class _WeakBuiltin(WeakCallback):
    def __init__(
        self,
        f: MethodWrapperType | BuiltinMethodType,
        max_args: int | None = None,
        finalize: Callable | None = None,
        on_ref_error: RefErrorChoice = "warn",
    ) -> None:
        super().__init__(f, max_args, on_ref_error)
        self._obj_ref = self._try_ref(f.__self__, finalize)
        self._func_name = f.__name__

    def cb(self, args: tuple[Any, ...] = ()) -> None:
        func = getattr(self._obj_ref(), self._func_name, None)
        if func is None:
            raise ReferenceError("weakly-referenced object no longer exists")
        if self._max_args is None:
            func(*args)
        else:
            func(*args[: self._max_args])

    def dereference(self) -> MethodWrapperType | BuiltinMethodType | None:
        return getattr(self._obj_ref(), self._func_name, None)


class _WeakSetattr(WeakCallback):
    """Caller to set an attribute on an object."""

    def __init__(
        self,
        obj: object,
        attr: str,
        max_args: int | None = None,
        finalize: Callable | None = None,
        on_ref_error: RefErrorChoice = "warn",
    ) -> None:
        super().__init__(obj, max_args, on_ref_error)
        self._obj_ref = self._try_ref(obj, finalize)
        self._attr = attr

    def cb(self, args: tuple[Any, ...] = ()) -> None:
        obj = self._obj_ref()
        if obj is None:
            raise ReferenceError("weakly-referenced object no longer exists")
        if self._max_args is not None:
            args = args[: self._max_args]
        setattr(obj, self._attr, args[0] if len(args) == 1 else args)

    def dereference(self) -> object | None:
        return self._obj_ref()


class _WeakSetitem(WeakCallback):
    """Caller to call __setitem__ on an object."""

    def __init__(
        self,
        obj: SupportsSetitem,
        key: Any,
        max_args: int | None = None,
        finalize: Callable | None = None,
        on_ref_error: RefErrorChoice = "warn",
    ) -> None:
        super().__init__(obj, max_args, on_ref_error)
        self._obj_ref = self._try_ref(obj, finalize)
        self._key = key

    def cb(self, args: tuple[Any, ...] = ()) -> None:
        obj = self._obj_ref()
        if obj is None:
            raise ReferenceError("weakly-referenced object no longer exists")
        if self._max_args is not None:
            args = args[: self._max_args]
        obj[self._key] = args[0] if len(args) == 1 else args

    def dereference(self) -> SupportsSetitem | None:
        return self._obj_ref()
