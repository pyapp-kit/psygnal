import sys
from functools import partial
from inspect import signature
from typing import Callable

import pytest

from psygnal import Signal, SignalInstance

if all(x not in {"--codspeed", "--benchmark", "tests/test_bench.py"} for x in sys.argv):
    pytest.skip("use --benchmark to run benchmark", allow_module_level=True)

CALLBACK_TYPES = [
    "function",
    "method",
    "lambda",
    "partial",
    "partial_method",
    "setattr",
    "setitem",
    "real_func",
    "print",
]

# fmt: off
class Emitter:
    one_int = Signal(int)
    int_str = Signal(int, str)


class Obj:
    x: int = 0
    def __setitem__(self, key: str, value: int) -> None:
        self.x = value
    def no_args(self) -> None: ...
    def one_int(self, x: int) -> None: ...
    def int_str(self, x: int, y: str) -> None: ...

def no_args() -> None: ...
def one_int(x: int) -> None: ...
def int_str(x: int, y: str) -> None: ...
def real_func() -> None: list(range(4))  # simulate a brief thing

INT_SIG = signature(one_int)
# fmt: on


def _get_callback(callback_type: str, obj: Obj) -> Callable:
    callback_types: dict[str, Callable] = {
        "function": one_int,
        "method": obj.one_int,
        "lambda": lambda x: None,
        "partial": partial(int_str, y="foo"),
        "partial_method": partial(obj.int_str, y="foo"),
        "real_func": real_func,
        "print": print,
    }
    return callback_types[callback_type]


# Creation suite ------------------------------------------


def test_create_signal(benchmark: Callable) -> None:
    benchmark(Signal, int)


def test_create_signal_instance(benchmark: Callable) -> None:
    benchmark(SignalInstance, INT_SIG)


# Connect suite ---------------------------------------------


@pytest.mark.parametrize("check_types", ["check_types", ""])
@pytest.mark.parametrize("callback_type", CALLBACK_TYPES)
def test_connect_time(
    benchmark: Callable, callback_type: str, check_types: str
) -> None:
    emitter = Emitter()
    obj = Obj()
    kwargs = {}
    if callback_type == "setattr":
        func: Callable = emitter.one_int.connect_setattr
        args: tuple = (obj, "x")
    elif callback_type == "setitem":
        func = emitter.one_int.connect_setitem
        args = (obj, "x")
    else:
        func = emitter.one_int.connect
        args = (_get_callback(callback_type, obj),)
        kwargs = {"check_types": bool(check_types)}

    benchmark(func, *args, **kwargs)


# Emit suite ------------------------------------------------


@pytest.mark.parametrize("n_connections", range(2, 2**6, 16))
@pytest.mark.parametrize("callback_type", CALLBACK_TYPES)
def test_emit_time(benchmark: Callable, n_connections: int, callback_type: str) -> None:
    emitter = Emitter()
    obj = Obj()
    if callback_type == "setattr":
        for _ in range(n_connections):
            emitter.one_int.connect_setattr(obj, "x")
    elif callback_type == "setitem":
        for _ in range(n_connections):
            emitter.one_int.connect_setitem(obj, "x")
    else:
        callback = _get_callback(callback_type, obj)
        for _ in range(n_connections):
            emitter.one_int.connect(callback, unique=False)

    benchmark(emitter.one_int.emit, 1)
