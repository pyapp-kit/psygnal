from unittest.mock import Mock, call

import numpy as np

from psygnal import SignalGroup
from psygnal.containers import (
    EventedCallableObjectProxy,
    EventedObjectProxy,
    _evented_proxy,
)
from psygnal.utils import monitor_events


def test_evented_proxy():
    class T:
        def __init__(self) -> None:
            self.x = 1
            self.f = "f"
            self._list = [0, 1]

        def __getitem__(self, key):
            return self._list[key]

        def __setitem__(self, key, value):
            self._list[key] = value

        def __delitem__(self, key):
            del self._list[key]

    t = EventedObjectProxy(T())
    assert "events" in dir(t)
    assert t.x == 1

    mock = Mock()
    with monitor_events(t.events, mock):
        t.x = 2
        t.f = "f"
        del t.x
        t.y = "new"
        t[0] = 7
        t[0] = 7  # no event
        del t[0]

    assert mock.call_args_list == [
        call("attribute_set", ("x", 2)),
        call("attribute_deleted", ("x",)),
        call("attribute_set", ("y", "new")),
        call("item_set", (0, 7)),
        call("item_deleted", (0,)),
    ]


def test_evented_proxy_ref():
    class T:
        def __init__(self) -> None:
            self.x = 1

    assert not _evented_proxy._OBJ_CACHE
    t = EventedObjectProxy(T())
    assert not _evented_proxy._OBJ_CACHE
    assert isinstance(t.events, SignalGroup)  # this will actually create the group
    assert len(_evented_proxy._OBJ_CACHE) == 1

    del t  # this should clean up the object from the cache
    assert not _evented_proxy._OBJ_CACHE


def test_in_place_proxies():
    # fmt: off
    class T:
        x = 0
        def __iadd__(self, other): return self  # noqa
        def __isub__(self, other): return self  # noqa
        def __imul__(self, other): return self  # noqa
        def __imatmul__(self, other): return self  # noqa
        def __itruediv__(self, other): return self  # noqa
        def __ifloordiv__(self, other): return self  # noqa
        def __imod__(self, other): return self  # noqa
        def __ipow__(self, other): return self  # noqa
        def __ilshift__(self, other): return self  # noqa
        def __irshift__(self, other): return self  # noqa
        def __iand__(self, other): return self  # noqa
        def __ixor__(self, other): return self  # noqa
        def __ior__(self, other): return self  # noqa
    # fmt: on

    t = EventedObjectProxy(T())
    mock = Mock()
    with monitor_events(t.events, mock):
        t += 1
        mock.assert_called_with("in_place", ("add", 1))
        t -= 2
        mock.assert_called_with("in_place", ("sub", 2))
        t *= 3
        mock.assert_called_with("in_place", ("mul", 3))
        t /= 4
        mock.assert_called_with("in_place", ("truediv", 4))
        t //= 5
        mock.assert_called_with("in_place", ("floordiv", 5))
        t @= 6
        mock.assert_called_with("in_place", ("matmul", 6))
        t %= 7
        mock.assert_called_with("in_place", ("mod", 7))
        t **= 8
        mock.assert_called_with("in_place", ("pow", 8))
        t <<= 9
        mock.assert_called_with("in_place", ("lshift", 9))
        t >>= 10
        mock.assert_called_with("in_place", ("rshift", 10))
        t &= 11
        mock.assert_called_with("in_place", ("and", 11))
        t ^= 12
        mock.assert_called_with("in_place", ("xor", 12))
        t |= 13
        mock.assert_called_with("in_place", ("or", 13))


def test_numpy_proxy():
    ary = np.ones((4, 4))
    t = EventedObjectProxy(ary)
    assert repr(t) == repr(ary)

    mock = Mock()
    with monitor_events(t.events, mock):
        t[0] = 2
        ((name, (key, value)), _) = tuple(mock.call_args)
        assert name == "item_set"
        assert key == 0
        assert np.array_equal(value, [2, 2, 2, 2])
        mock.reset_mock()

        t[2:] = np.arange(8).reshape(2, 4)

        ((name, (key, value)), _) = tuple(mock.call_args)
        assert name == "item_set"
        assert key == slice(2, None, None)
        assert np.array_equal(value, [[0, 1, 2, 3], [4, 5, 6, 7]])
        mock.reset_mock()

        t += 1
        t -= 1
        assert np.array_equal(
            t, np.asarray([[2, 2, 2, 2], [1, 1, 1, 1], [0, 1, 2, 3], [4, 5, 6, 7]])
        )
        t *= [0, 0, 0, 0]
        assert not t.any()

    assert mock.call_args_list == [
        call("in_place", ("add", 1)),
        call("in_place", ("sub", 1)),
        call("in_place", ("mul", [0, 0, 0, 0])),
    ]


def test_evented_callable_proxy():
    calls = []

    def f(*args, **kwargs):
        calls.append((args, kwargs))

    ef = EventedCallableObjectProxy(f)
    ef(1, 2, foo="bar")
    assert calls == [((1, 2), {"foo": "bar"})]
