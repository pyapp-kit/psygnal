from __future__ import annotations

import types
import weakref
from functools import partial
from typing import Any, Callable, TypeVar

_T = TypeVar("_T")


class weak_callable:
    __slots__ = ("_id", "_max_args", "_args", "_kwds", "_alive", "_callable")

    def __init__(
        self,
        obj: Callable,
        *args: Any,
        max_args: int | None = None,
        callback: Callable | None = None,
        **kwargs: Any,
    ) -> None:
        if isinstance(obj, partial):
            args = obj.args + args
            kwargs = {**obj.keywords, **kwargs}
            obj = obj.func

        self._id = self._hash(obj, args, kwargs)
        self._max_args = max_args
        self._args = args
        self._kwds = kwargs

        self._alive = True

        def _cb(_: Any) -> Any:
            # The self-weakref trick is needed to avoid creating a reference cycle
            if self._alive:
                self._alive = False
                if callback is not None:
                    callback(self)

        self._callable = self._weak_caller(obj, _cb)

    def __call__(self, args: tuple) -> bool:
        if self._max_args is not None:
            args = args[: self._max_args]
        try:
            self._callable(*self._args, *args, **self._kwds)
        except ReferenceError:
            return True
        return False

    def __eq__(self, other: object) -> bool:
        # sourcery skip: assign-if-exp, reintroduce-else
        if isinstance(other, weak_callable):
            return self._id == other._id
        return False

    @property
    def name(self) -> str:
        return str(self._id)

    @staticmethod
    def _weak_caller(obj: Any, callback: Callable | None = None) -> Callable:
        if isinstance(obj, types.MethodType):
            _obj_ref = weakref.ref(obj.__self__, callback)
            _func_ref = weakref.ref(obj.__func__, callback)

            def _call_method(*_args: Any, **_kwds: Any) -> Any:
                obj = _obj_ref()
                func = _func_ref()
                if obj is None or func is None:
                    raise ReferenceError("weakly-referenced object no longer exists")
                return func(obj, *_args, **_kwds)

            return _call_method
        elif isinstance(obj, (types.MethodWrapperType, types.BuiltinMethodType)):
            _obj_proxy = weak_callable.try_proxy(obj.__self__, callback)
            _func_name = obj.__name__

            def _call_method_wrapper(*_args: Any, **_kwds: Any) -> Any:
                func = getattr(_obj_proxy, _func_name)
                return func(*_args, **_kwds)

            return _call_method_wrapper

        elif isinstance(obj, types.FunctionType):
            # TODO...
            return obj  # strong ref for now

        raise

    @staticmethod
    def try_proxy(
        obj: _T, callback: Callable | None = None
    ) -> weakref.ProxyType[_T] | _T:
        try:
            return weakref.proxy(obj, callback)  # type: ignore
        except TypeError:
            # TODO: warn?
            return obj

    @staticmethod
    def _hash(obj: Callable, args: tuple = (), kwargs: dict | None = None) -> int:
        if isinstance(obj, (types.MethodType, types.MethodWrapperType)):
            h = hash(obj.__self__) + hash(obj.__name__)
        else:
            h = hash(obj)
        return h + hash(args)
