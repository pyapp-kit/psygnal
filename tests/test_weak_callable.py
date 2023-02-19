from functools import partial
from unittest.mock import Mock

import pytest

from psygnal._weak_callback import WeakCallback, weak_callback


@pytest.mark.parametrize(
    "type_",
    [
        "function",
        "weak_func",
        "lambda",
        "method",
        "partial_method",
        "setattr",
        "setitem",
        "mock",
        "weak_cb",
        "print",
    ],
)
def test_slot_types(type_: str, capsys) -> None:
    mock = Mock()
    final_mock = Mock()

    class MyObj:
        def method(self, x: int) -> None:
            mock(x)

        def __setitem__(self, key, value):
            mock(value)

        def __setattr__(self, __name: str, __value) -> None:
            if __name == "x":
                mock(__value)

    obj = MyObj()

    if type_ == "setattr":
        cb = weak_callback(setattr, obj, "x", finalize=final_mock)
    elif type_ == "setitem":
        cb = weak_callback(obj.__setitem__, "x", finalize=final_mock)
    elif type_ in {"function", "weak_func"}:

        def obj(x: int) -> None:
            mock(x)

        cb = weak_callback(obj, strong_func=(type_ == "function"), finalize=final_mock)
    elif type_ == "lambda":
        cb = weak_callback(lambda x: mock(x), finalize=final_mock)
    elif type_ == "method":
        cb = weak_callback(obj.method, finalize=final_mock)
    elif type_ == "partial_method":
        cb = weak_callback(partial(obj.method, 2), max_args=0, finalize=final_mock)
    elif type_ == "mock":
        cb = weak_callback(mock, finalize=final_mock)
    elif type_ == "weak_cb":
        cb = weak_callback(obj.method, finalize=final_mock)
        cb = weak_callback(cb, finalize=final_mock)
    elif type_ == "print":
        cb = weak_callback(print, finalize=final_mock)

    assert isinstance(cb, WeakCallback)
    cb.cb((2,))
    assert cb.dereference() is not None
    if type_ == "print":
        assert capsys.readouterr().out == "2\n"
        return

    mock.assert_called_once_with(2)
    del obj

    if type_ not in ("function", "lambda", "mock"):
        final_mock.assert_called_once_with(cb)
        assert cb.dereference() is None
        with pytest.raises(ReferenceError):
            cb.cb((2,))
    else:
        cb.cb((4,))
        mock.assert_called_with(4)
