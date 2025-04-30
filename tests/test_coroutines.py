import asyncio
import gc
from typing import Any
from unittest.mock import Mock

import pytest

from psygnal import _async
from psygnal._weak_callback import WeakCallback, weak_callback


@pytest.mark.parametrize(
    "type_",
    [
        "coroutinefunc",
        "weak_coroutinefunc",
        "coroutinemethod",
    ],
)
@pytest.mark.asyncio
async def test_slot_types(type_: str, capsys: Any) -> None:
    backend = _async.set_async_backend("asyncio")
    assert backend is _async.get_async_backend() is not None
    while not backend.running:
        await asyncio.sleep(0)

    mock = Mock()
    final_mock = Mock()

    obj: Any
    if type_ in {"coroutinefunc", "weak_coroutinefunc"}:

        async def obj(x: int) -> int:
            mock(x)
            return x

        cb = weak_callback(
            obj, strong_func=(type_ == "coroutinefunc"), finalize=final_mock
        )
    elif type_ == "coroutinemethod":

        class MyObj:
            async def coroutine_method(self, x: int) -> int:
                mock(x)
                return x

        obj = MyObj()
        cb = weak_callback(obj.coroutine_method, finalize=final_mock)

    assert isinstance(cb, WeakCallback)
    assert isinstance(cb.slot_repr(), str)
    assert cb.dereference() is not None

    cb.cb((2,))
    await asyncio.sleep(0.01)
    mock.assert_called_once_with(2)

    mock.reset_mock()
    assert await cb(4) == 4
    mock.assert_called_once_with(4)

    del obj
    gc.collect()
    await asyncio.sleep(0.01)

    if type_ == "coroutinefunc":  # strong_func
        cb.cb((4,))
        await asyncio.sleep(0.01)
        mock.assert_called_with(4)

    else:
        final_mock.assert_called_once_with(cb)
        assert cb.dereference() is None
        with pytest.raises(ReferenceError):
            cb.cb((2,))
            await asyncio.sleep(0.01)
        with pytest.raises(ReferenceError):
            await cb(2)
