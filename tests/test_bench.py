import sys
from functools import partial
from inspect import signature
from typing import Callable

import pytest

from psygnal import Signal, SignalInstance

if all(x not in {"--codspeed", "--benchmark", "tests/test_bench.py"} for x in sys.argv):
    pytest.skip("use --benchmark to run benchmark", allow_module_level=True)


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


@pytest.mark.benchmark
def test_create_signal() -> None:
    _ = Signal(int)


@pytest.mark.benchmark
def test_create_signal_instance() -> None:
    _ = SignalInstance(INT_SIG)


@pytest.mark.benchmark
def test_connect_function(benchmark: Callable) -> None:
    emitter = Emitter()
    benchmark(emitter.int_str.connect, int_str)


@pytest.mark.benchmark
def test_connect_function_typed(benchmark: Callable) -> None:
    emitter = Emitter()
    benchmark(emitter.int_str.connect, int_str, check_types=True)


@pytest.mark.benchmark
def test_connect_method(benchmark: Callable) -> None:
    emitter = Emitter()
    obj = Obj()
    benchmark(emitter.int_str.connect, obj.int_str)


@pytest.mark.benchmark
def test_connect_method_typed(benchmark: Callable) -> None:
    emitter = Emitter()
    obj = Obj()
    benchmark(emitter.int_str.connect, obj.int_str, check_types=True)


@pytest.mark.benchmark
@pytest.mark.parametrize("n_connections", range(2, 2**6, 16))
@pytest.mark.parametrize(
    "callback_type",
    [
        "function",
        "method",
        "lambda",
        "partial",
        "partial_method",
        "real_func",
        "setattr",
        "setitem",
    ],
)
def test_emit_time(benchmark: Callable, n_connections: int, callback_type: str) -> None:
    emitter = Emitter()
    obj = Obj()
    callback_types: dict[str, Callable] = {
        "function": one_int,
        "method": obj.one_int,
        "lambda": lambda x: None,
        "partial": partial(int_str, y="foo"),
        "partial_method": partial(obj.int_str, y="foo"),
        "real_func": real_func,
    }
    if callback_type == "setattr":
        for _ in range(n_connections):
            emitter.one_int.connect_setattr(obj, "x")
    elif callback_type == "setitem":
        for _ in range(n_connections):
            emitter.one_int.connect_setitem(obj, "x")
    else:
        callback = callback_types[callback_type]
        for _ in range(n_connections):
            emitter.one_int.connect(callback, unique=False)

    benchmark(emitter.one_int.emit, 1)
