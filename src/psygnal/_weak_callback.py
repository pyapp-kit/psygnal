from __future__ import annotations

import weakref
from functools import partial
from types import BuiltinMethodType, FunctionType, MethodType, MethodWrapperType
from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar, cast
from warnings import warn

from typing_extensions import Protocol

if TYPE_CHECKING:
    from typing_extensions import Literal, TypeAlias

    RefErrorChoice: TypeAlias = Literal["raise", "warn", "ignore"]

__all__ = ["weak_callback", "WeakCallback"]
_T = TypeVar("_T")
_R = TypeVar("_R")  # return type of cb


def weak_callback(
    cb: Callable[..., _R] | WeakCallback[_R],
    *args: Any,
    max_args: int | None = None,
    finalize: Callable[[WeakCallback], Any] | None = None,
    strong_func: bool = True,
    on_ref_error: RefErrorChoice = "warn",
) -> WeakCallback[_R]:
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
        reasoning for this is that functions and lambdas are very often defined *only*
        to be passed to this function, and would likely be immediately garbage
        collected if we weakly referenced them. If you would specifically like to
        *allow* the function to be garbage collected, set this to False.
    on_ref_error : {'raise', 'warn', 'ignore'}, optional
        What to do if a weak reference cannot be created.  If 'raise', a
        ReferenceError will be raised.  If 'warn' (default), a warning will be issued
        and a strong-reference will be used. If 'ignore' a strong-reference will be
        used (silently).

    Returns
    -------
    WeakCallback
        A WeakCallback subclass instance appropriate for the given callable.
        The fast way to "call" the callback is to use the `cb` method, passing a
        single args tuple, it returns nothing.  A `__call__` method is also provided,
        that can be used to call the original function as usual.

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

    kwargs: dict[str, Any] | None = None
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
        if kwargs:  # pragma: no cover
            raise NotImplementedError(
                "MethodWrapperTypes do not support keyword arguments"
            )

        if cb is setattr:
            try:
                obj, attr = args[:2]
            except IndexError as e:  # pragma: no cover
                raise TypeError(
                    "setattr requires two arguments, an object and an attribute name."
                ) from e
            return _WeakSetattr(obj, attr, max_args, finalize, on_ref_error)
        return _WeakBuiltin(cb, max_args, args, finalize, on_ref_error)

    if callable(cb):
        return _WeakFunction(cb, max_args, args, kwargs, finalize, on_ref_error)

    raise TypeError(f"unsupported type {type(cb)}")  # pragma: no cover


class WeakCallback(Generic[_R]):
    """Abstract Base Class for weakly-referenced callbacks.

    Do not instantiate this class directly, use the `weak_callback` function instead.
    The main public-facing methods of all subclasses are:

        cb(args: tuple[Any, ...] = ()) -> None: special fast callback method, args only.
        dereference() -> Callable[..., _R] | None: return strong dereferenced callback.
        __call__(*args: Any, **kwargs: Any) -> _R: call original callback
        __eq__: compare two WeakCallback instances for equality
        object_key: static method that returns a unique key for an object.

    NOTE: can't use ABC here because then mypyc and PySide2 don't play nice together.
    """

    def __init__(
        self,
        obj: Any,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
    ) -> None:
        self._key: str = WeakCallback.object_key(obj)
        self._max_args: int | None = max_args
        self._alive: bool = True
        self._on_ref_error: RefErrorChoice = on_ref_error

    def cb(self, args: tuple[Any, ...] = ()) -> None:
        """Call the callback with `args`. Args will be spread when calling the func."""
        raise NotImplementedError()

    def dereference(self) -> Callable[..., _R] | None:
        """Return the original object, or None if dead."""
        raise NotImplementedError()

    def __call__(self, *args: Any, **kwds: Any) -> _R:
        func = self.dereference()
        if func is None:
            raise ReferenceError("callback is dead")
        if self._max_args is not None:
            args = args[: self._max_args]
        return func(*args, **kwds)

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
                warn(f"failed to create weakref for {obj!r}, returning strong ref")

            def _strong_ref() -> _T:
                return obj

            return _strong_ref

    @staticmethod
    def object_key(obj: Any) -> str:
        """Return a unique key for an object.

        This includes information about the object's type, module, and id. It has
        considerations for bound methods (which would otherwise have a different id
        for each instance).
        """
        if hasattr(obj, "__self__"):
            # bound method ... don't take the id of the bound method itself.
            obj_id = id(obj.__self__)
            owner_cls = type(obj.__self__)
            type_name = getattr(owner_cls, "__name__", None) or ""
            module = getattr(owner_cls, "__module__", None) or ""
            method_name = getattr(obj, "__name__", None) or ""
            obj_name = f"{type_name}.{method_name}"
        else:
            obj_id = id(obj)
            module = getattr(obj, "__module__", None) or ""
            obj_name = getattr(obj, "__name__", None) or ""
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
    """Wrapper around a strong function reference."""

    def __init__(
        self,
        obj: Callable,
        max_args: int | None = None,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        on_ref_error: RefErrorChoice = "warn",
    ) -> None:
        super().__init__(obj, max_args, on_ref_error)
        self._f = obj
        self._args = args
        self._kwargs = kwargs or {}

    def cb(self, args: tuple[Any, ...] = ()) -> None:
        if self._max_args is not None:
            args = args[: self._max_args]
        self._f(*self._args, *args, **self._kwargs)

    def dereference(self) -> Callable:
        if self._args or self._kwargs:
            return partial(self._f, *self._args, **self._kwargs)
        return self._f


class _WeakFunction(WeakCallback):
    """Wrapper around a weak function reference."""

    def __init__(
        self,
        obj: Callable,
        max_args: int | None = None,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        finalize: Callable | None = None,
        on_ref_error: RefErrorChoice = "warn",
    ) -> None:
        super().__init__(obj, max_args, on_ref_error)
        self._f = self._try_ref(obj, finalize)
        self._args = args
        self._kwargs = kwargs or {}

    def cb(self, args: tuple[Any, ...] = ()) -> None:
        f = self._f()
        if f is None:
            raise ReferenceError("weakly-referenced object no longer exists")
        if self._max_args is not None:
            args = args[: self._max_args]
        f(*self._args, *args, **self._kwargs)

    def dereference(self) -> Callable | None:
        f = self._f()
        if f is None:
            return None
        if self._args or self._kwargs:
            return partial(f, *self._args, **self._kwargs)
        return f


class _WeakMethod(WeakCallback):
    """Wrapper around a method bound to a weakly-referenced object.

    Bound methods have a `__self__` attribute that holds a strong reference to the
    object they are bound to and a `__func__` attribute that holds a reference
    to the function that implements the method (on the class level)

    When `cb` is called here, it dereferences the two, and calls:
    `obj.__func__(obj.__self__, *args, **kwargs)`
    """

    def __init__(
        self,
        obj: MethodType,
        max_args: int | None = None,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        finalize: Callable | None = None,
        on_ref_error: RefErrorChoice = "warn",
    ) -> None:
        super().__init__(obj.__self__, max_args, on_ref_error)
        self._obj_ref = self._try_ref(obj.__self__, finalize)
        self._func_ref = self._try_ref(obj.__func__, finalize)
        self._args = args
        self._kwargs = kwargs or {}

    def cb(self, args: tuple[Any, ...] = ()) -> None:
        obj = self._obj_ref()
        func = self._func_ref()
        if obj is None or func is None:
            raise ReferenceError("weakly-referenced object no longer exists")

        if self._max_args is not None:
            args = args[: self._max_args]
        func(obj, *self._args, *args, **self._kwargs)

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
    """Wrapper around a c-based method on a weakly-referenced object.

    Builtin/extension methods do have a `__self__` attribute (the object to which they
    are bound), but don't have a __func__ attribute, so we need to store the name of the
    method and look it up on the object when the callback is called.

    When `cb` is called here, it dereferences the object, and calls:
    `getattr(obj.__self__, obj.__name__)(*args, **kwargs)`
    """

    def __init__(
        self,
        obj: MethodWrapperType | BuiltinMethodType,
        max_args: int | None = None,
        args: tuple[Any, ...] = (),
        finalize: Callable | None = None,
        on_ref_error: RefErrorChoice = "warn",
    ) -> None:
        super().__init__(obj, max_args, on_ref_error)
        self._obj_ref = self._try_ref(obj.__self__, finalize)
        self._func_name = obj.__name__
        self._args = args

    def cb(self, args: tuple[Any, ...] = ()) -> None:
        func = getattr(self._obj_ref(), self._func_name, None)
        if func is None:
            raise ReferenceError("weakly-referenced object no longer exists")
        if self._max_args is None:
            func(*self._args, *args)
        else:
            func(*self._args, *args[: self._max_args])

    def dereference(self) -> MethodWrapperType | BuiltinMethodType | None:
        return getattr(self._obj_ref(), self._func_name, None)


class _WeakSetattr(WeakCallback):
    """Caller to set an attribute on a weakly-referenced object."""

    def __init__(
        self,
        obj: object,
        attr: str,
        max_args: int | None = None,
        finalize: Callable | None = None,
        on_ref_error: RefErrorChoice = "warn",
    ) -> None:
        super().__init__(obj, max_args, on_ref_error)
        self._key += f".__setattr__({attr!r})"
        self._obj_ref = self._try_ref(obj, finalize)
        self._attr = attr

    def cb(self, args: tuple[Any, ...] = ()) -> None:
        obj = self._obj_ref()
        if obj is None:
            raise ReferenceError("weakly-referenced object no longer exists")
        if self._max_args is not None:
            args = args[: self._max_args]
        setattr(obj, self._attr, args[0] if len(args) == 1 else args)

    def dereference(self) -> partial | None:
        obj = self._obj_ref()
        return None if obj is None else partial(setattr, obj, self._attr)


class SupportsSetitem(Protocol):
    def __setitem__(self, key: Any, value: Any) -> None:
        ...


class _WeakSetitem(WeakCallback):
    """Caller to call __setitem__ on a weakly-referenced object."""

    def __init__(
        self,
        obj: SupportsSetitem,
        key: Any,
        max_args: int | None = None,
        finalize: Callable | None = None,
        on_ref_error: RefErrorChoice = "warn",
    ) -> None:
        super().__init__(obj, max_args, on_ref_error)
        self._key += f".__setitem__({key!r})"
        self._obj_ref = self._try_ref(obj, finalize)
        self._itemkey = key

    def cb(self, args: tuple[Any, ...] = ()) -> None:
        obj = self._obj_ref()
        if obj is None:
            raise ReferenceError("weakly-referenced object no longer exists")
        if self._max_args is not None:
            args = args[: self._max_args]
        obj[self._itemkey] = args[0] if len(args) == 1 else args

    def dereference(self) -> partial | None:
        obj = self._obj_ref()
        return None if obj is None else partial(obj.__setitem__, self._itemkey)
