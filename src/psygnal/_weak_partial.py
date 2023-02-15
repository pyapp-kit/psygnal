from __future__ import annotations

import types
import weakref
from functools import partial
from typing import Any, Callable, Generic, TypeVar

_T = TypeVar("_T")
_R = TypeVar("_R")


class weak_partial(Generic[_R]):
    __slots__ = ("_id", "_max_args", "_args", "_kwds", "_alive", "_callable")

    def __init__(
        self,
        obj: Callable[..., _R],
        *args: Any,
        max_args: int | None = None,
        finalize: Callable[[weak_partial], Any] | None = None,
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

        def _cb(_: Any) -> None:
            # The self-weakref trick is needed to avoid creating a reference cycle
            if self._alive:
                self._alive = False
                if finalize is not None:
                    finalize(self)

        self._callable = self._weak_caller(obj, _cb)

    def _clip_args(self, args: tuple) -> tuple:
        return args if self._max_args is None else args[: self._max_args]

    def cb(self, args: tuple[Any, ...]) -> None:
        """Faster version of __call__ for use in weakref callbacks."""
        self._callable(*self._args, *self._clip_args(args), **self._kwds)

    def __call__(self, *args: Any, **kwargs: Any) -> _R:
        return self._callable(
            *self._args, *self._clip_args(args), **{**self._kwds, **kwargs}
        )

    def __eq__(self, other: object) -> bool:
        # sourcery skip: assign-if-exp, reintroduce-else
        if isinstance(other, weak_partial):
            return self._id == other._id
        return NotImplemented

    @property
    def name(self) -> str:
        return str(self._id)

    @staticmethod
    def _weak_caller(
        obj: Callable[..., _R], callback: Callable | None = None
    ) -> Callable[..., _R]:
        if isinstance(obj, types.FunctionType):
            # TODO... clarify this behavior
            # strong ref for now, because very often, when function is passed
            # as a callback, it might be the *only* reference to it and we
            # don't want it to be garbage collected.
            return obj
        elif isinstance(obj, types.MethodType):
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
            _obj_proxy = weak_partial.try_proxy(obj.__self__, callback)
            _func_name = obj.__name__

            def _call_method_wrapper(*_args: Any, **_kwds: Any) -> Any:
                func = getattr(_obj_proxy, _func_name)
                return func(*_args, **_kwds)

            return _call_method_wrapper
        elif callable(obj):
            return weak_partial.try_proxy(obj, callback)  # type: ignore
        raise TypeError(f"Cannot create weak_callable for {type(obj)} object")

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
