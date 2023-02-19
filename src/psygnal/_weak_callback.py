from __future__ import annotations

import weakref
from functools import partial
from types import BuiltinMethodType, FunctionType, MethodType, MethodWrapperType
from typing import Any, Callable, Literal, Protocol, SupportsIndex, TypeVar
from warnings import warn

_T = TypeVar("_T")


class SupportsSetitem(Protocol):
    def __setitem__(self, key: Any, value: Any) -> None:
        ...


SupportsIndex


class WeakCallback:
    def __init__(
        self,
        obj: Any,
        max_args: int | None = None,
    ) -> None:
        mod = getattr(obj, "__module__", None) or ""
        name = getattr(obj, "__name__", None) or ""
        self._key = f"{mod}:{name}@{hex(id(obj))}"
        self._max_args = max_args
        self._alive = True

    def cb(self, args: tuple[Any, ...]) -> None:
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
        on_error: Literal["raise", "warn", "ignore"] = "warn",
    ) -> Callable[[], _T | None]:
        _cb = None if finalize is None else _kill_and_finalize(self, finalize)
        try:
            return weakref.ref(obj, _cb)
        except TypeError:
            if on_error == "raise":
                raise
            if on_error == "warn":
                # FIXME: special case (move me)
                mod = getattr(obj, "__module__", None) or ""
                if "QtCore" not in mod:
                    warn(f"failed to create weakref for {obj!r}, returning strong ref")

            def _strong_ref() -> _T:
                return obj

            return _strong_ref


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
        f: FunctionType,
        max_args: int | None = None,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(f, max_args)
        self._f = f
        self._args = args
        self._kwargs = kwargs or {}
        self._args = args
        self._kwargs = kwargs or {}

    def cb(self, args: tuple[Any, ...]) -> None:
        if self._max_args is None:
            if self._kwargs:
                self._f(*self._args, *args, **self._kwargs)
            else:
                self._f(*self._args, *args)
        elif self._kwargs:
            self._f(*self._args, *args[: self._max_args], **self._kwargs)
        else:
            self._f(*self._args, *args[: self._max_args])

    def ref(self) -> FunctionType:
        return self._f


class _WeakFunction(WeakCallback):
    def __init__(
        self,
        f: Callable,
        max_args: int | None = None,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        finalize: Callable | None = None,
    ) -> None:
        super().__init__(f, max_args)
        self._f = self._try_ref(f, finalize)
        self._args = args
        self._kwargs = kwargs or {}

    def cb(self, args: tuple[Any, ...]) -> None:
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

    def ref(self) -> Callable | None:
        return self._f()


class _WeakMethod(WeakCallback):
    def __init__(
        self,
        f: MethodType,
        max_args: int | None = None,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        finalize: Callable | None = None,
    ) -> None:
        super().__init__(f.__self__, max_args)
        self._args = args
        self._obj_ref = self._try_ref(f.__self__, finalize)
        self._func_ref = self._try_ref(f.__func__, finalize)
        self._kwargs = kwargs or {}

    def cb(self, args: tuple[Any, ...]) -> None:
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

    def ref(self) -> MethodType | None:
        obj = self._obj_ref()
        func = self._func_ref()
        return None if obj is None or func is None else func.__get__(obj)


class _WeakBuiltin(WeakCallback):
    def __init__(
        self,
        f: MethodWrapperType | BuiltinMethodType,
        max_args: int | None = None,
        finalize: Callable | None = None,
    ) -> None:
        super().__init__(f, max_args)
        self._obj_ref = self._try_ref(f.__self__, finalize)
        self._func_name = f.__name__

    def cb(self, args: tuple[Any, ...]) -> None:
        obj = self._obj_ref()
        func = getattr(obj, self._func_name, None)
        if obj is None or func is None:
            raise ReferenceError("weakly-referenced object no longer exists")
        if self._max_args is None:
            func(*args)
        else:
            func(*args[: self._max_args])

    def ref(self) -> MethodWrapperType | BuiltinMethodType | None:
        obj = self._obj_ref()
        func = getattr(obj, self._func_name, None)
        return None if obj is None or func is None else func.__get__(obj)


class _WeakSetattr(WeakCallback):
    """Caller to set an attribute on an object."""

    def __init__(
        self,
        obj: object,
        attr: str,
        max_args: int | None = None,
        finalize: Callable | None = None,
    ) -> None:
        super().__init__(obj, max_args)
        self._obj_ref = self._try_ref(obj, finalize)
        self._attr = attr

    def cb(self, args: tuple[Any, ...]) -> None:
        obj = self._obj_ref()
        if obj is None:
            raise ReferenceError("weakly-referenced object no longer exists")
        if self._max_args is not None:
            args = args[: self._max_args]
        setattr(obj, self._attr, args[0] if len(args) == 1 else args)

    def ref(self) -> object | None:
        return self._obj_ref()


class _WeakSetitem(WeakCallback):
    """Caller to set an attribute on an object."""

    def __init__(
        self,
        obj: SupportsSetitem,
        key: Any,
        max_args: int | None = None,
        finalize: Callable | None = None,
    ) -> None:
        super().__init__(obj, max_args)
        self._obj_ref = self._try_ref(obj, finalize)
        self._key = key

    def cb(self, args: tuple[Any, ...]) -> None:
        obj = self._obj_ref()
        if obj is None:
            raise ReferenceError("weakly-referenced object no longer exists")
        if self._max_args is not None:
            args = args[: self._max_args]
        obj[self._key] = args[0] if len(args) == 1 else args

    def ref(self) -> SupportsSetitem | None:
        return self._obj_ref()


def weak_callback(
    cb: Callable,
    *args: Any,
    max_args: int | None = None,
    finalize: Callable[[WeakCallback], Any] | None = None,
    strong_func: bool = True,
) -> WeakCallback:
    if isinstance(cb, WeakCallback):
        return cb

    kwargs = None
    if isinstance(cb, partial):
        if max_args is not None:
            nargs = len(cb.args)
            if nargs:
                max_args += nargs
        args = cb.args + args
        kwargs = cb.keywords
        cb = cb.func

    if isinstance(cb, FunctionType):
        return (
            _StrongFunction(cb, max_args, args, kwargs)
            if strong_func
            else _WeakFunction(cb, max_args, args, kwargs, finalize)
        )

    if isinstance(cb, MethodType):
        return _WeakMethod(cb, max_args, args, kwargs, finalize)

    if isinstance(cb, (MethodWrapperType, BuiltinMethodType)):
        if cb is setattr:
            obj, attr, *_ = args
            return _WeakSetattr(obj, attr, max_args=max_args, finalize=finalize)
        return _WeakBuiltin(cb, max_args, finalize)

    if callable(cb):
        return _WeakFunction(cb, max_args, args, kwargs, finalize)

    raise TypeError(f"unsupported type {type(cb)}")
