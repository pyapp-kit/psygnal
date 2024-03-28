import gc
import re
from functools import partial
from typing import Any
from unittest.mock import Mock
from weakref import ref

import pytest

from psygnal import SignalInstance
from psygnal._weak_callback import WeakCallback, weak_callback


@pytest.mark.parametrize(
    "type_",
    [
        "function",
        "toolz_function",
        "weak_func",
        "lambda",
        "method",
        "partial_method",
        "toolz_method",
        "setattr",
        "setitem",
        "mock",
        "weak_cb",
        "print",
    ],
)
def test_slot_types(type_: str, capsys: Any) -> None:
    mock = Mock()
    final_mock = Mock()

    class MyObj:
        def method(self, x: int) -> None:
            mock(x)
            return x

        def __setitem__(self, key, value):
            mock(value)
            return value

        def __setattr__(self, __name: str, __value) -> None:
            if __name == "x":
                mock(__value)
                return __value

    obj = MyObj()

    if type_ == "setattr":
        cb = weak_callback(setattr, obj, "x", finalize=final_mock)
    elif type_ == "setitem":
        cb = weak_callback(obj.__setitem__, "x", finalize=final_mock)
    elif type_ in {"function", "weak_func"}:

        def obj(x: int) -> None:
            mock(x)
            return x

        cb = weak_callback(obj, strong_func=(type_ == "function"), finalize=final_mock)
    elif type_ == "toolz_function":
        toolz = pytest.importorskip("toolz")

        @toolz.curry
        def obj(z: int, x: int) -> None:
            mock(x)
            return x

        cb = weak_callback(obj(5), finalize=final_mock)
    elif type_ == "lambda":
        cb = weak_callback(lambda x: mock(x) and x, finalize=final_mock)
    elif type_ == "method":
        cb = weak_callback(obj.method, finalize=final_mock)
    elif type_ == "partial_method":
        cb = weak_callback(partial(obj.method, 2), max_args=0, finalize=final_mock)
    elif type_ == "toolz_method":
        toolz = pytest.importorskip("toolz")
        cb = weak_callback(toolz.curry(obj.method, 2), max_args=0, finalize=final_mock)
    elif type_ == "mock":
        cb = weak_callback(mock, finalize=final_mock)
    elif type_ == "weak_cb":
        cb = weak_callback(obj.method, finalize=final_mock)
        cb = weak_callback(cb, finalize=final_mock)
    elif type_ == "print":
        cb = weak_callback(print, finalize=final_mock)

    assert isinstance(cb, WeakCallback)
    assert isinstance(cb.slot_repr(), str)
    cb.cb((2,))
    assert cb.dereference() is not None
    if type_ == "print":
        assert capsys.readouterr().out == "2\n"
        return

    mock.assert_called_once_with(2)
    mock.reset_mock()
    result = cb(2)
    if type_ not in ("setattr", "mock"):
        assert result == 2
    mock.assert_called_once_with(2)

    del obj

    if type_ not in ("function", "toolz_function", "lambda", "mock"):
        final_mock.assert_called_once_with(cb)
        assert cb.dereference() is None
        with pytest.raises(ReferenceError):
            cb.cb((2,))
        with pytest.raises(ReferenceError):
            cb(2)
    else:
        cb.cb((4,))
        mock.assert_called_with(4)


def test_weak_callable_equality() -> None:
    """Slot callers should be equal only if they represent the same bound-method."""

    class T:
        def x(self): ...

    t1 = T()
    t2 = T()
    t1_ref = ref(t1)
    t2_ref = ref(t2)

    bmt1_a = weak_callback(t1.x)
    bmt1_b = weak_callback(t1.x)
    bmt2_a = weak_callback(t2.x)
    bmt2_b = weak_callback(t2.x)

    assert bmt1_a != "not a weak callback"

    def _assert_equality() -> None:
        assert bmt1_a == bmt1_b
        assert bmt2_a == bmt2_b
        assert bmt1_a != bmt2_a
        assert bmt1_b != bmt2_b

    _assert_equality()
    del t1
    gc.collect()
    assert t1_ref() is None
    _assert_equality()
    del t2
    gc.collect()
    assert t2_ref() is None
    _assert_equality()


def test_nonreferencable() -> None:
    class T:
        __slots__ = ("x",)

        def method(self) -> None: ...

    t = T()
    with pytest.warns(UserWarning, match="failed to create weakref"):
        cb = weak_callback(t.method)
        assert cb.dereference() == t.method

    with pytest.raises(TypeError):
        weak_callback(t.method, on_ref_error="raise")

    cb = weak_callback(t.method, on_ref_error="ignore")
    assert cb.dereference() == t.method


@pytest.mark.parametrize("strong", [True, False])
def test_deref(strong: bool) -> None:
    def func(x): ...

    p = partial(func, 1)
    cb = weak_callback(p, strong_func=strong)
    dp = cb.dereference()

    assert dp.func is p.func
    assert dp.args == p.args
    assert dp.keywords == p.keywords


def test_queued_callbacks() -> None:
    from psygnal._queue import QueuedCallback

    def func(x):
        return x

    cb = weak_callback(func)
    qcb = QueuedCallback(cb, thread="current")

    assert qcb.dereference() is func
    assert qcb(1) == 1


def test_cb_raises() -> None:
    from psygnal import EmitLoopError

    sig = SignalInstance((int,), name="sig")

    class T:
        @property
        def x(self) -> int:
            return 1

        @x.setter
        def x(self, value: int) -> None:
            1 / value

        def __setitem__(self, key: str, value: int) -> Any:
            1 / value

        def method(self, x: int) -> None:
            1 / x

    t = T()

    sig.connect(t.method)
    error_re = re.compile(
        f"emitting signal.*'sig'.*{re.escape(__file__)}.*method", re.DOTALL
    )
    with pytest.raises(EmitLoopError, match=error_re):
        sig.emit("a")
    sig.disconnect(t.method)

    sig.connect_setattr(t, "x", maxargs=1)
    error_re = re.compile(
        f"emitting signal.*'sig'.*{re.escape(__file__)}.*x", re.DOTALL
    )
    with pytest.raises(EmitLoopError, match=error_re):
        sig.emit("a")
    sig.disconnect_setattr(t, "x")

    sig.connect_setitem(t, "x", maxargs=1)
    error_re = re.compile(
        f"emitting signal.*'sig'.*{re.escape(__file__)}.*__setitem__", re.DOTALL
    )
    with pytest.raises(EmitLoopError, match=error_re):
        sig.emit("a")
