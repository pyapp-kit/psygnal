import sys
from dataclasses import dataclass
from functools import partial
from inspect import signature
from typing import Callable, ClassVar
from unittest.mock import Mock

import pytest

from psygnal import EmissionInfo, Signal, SignalGroupDescriptor, SignalInstance, evented

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
        kwargs = {"maxargs": 1}
    elif callback_type == "setitem":
        func = emitter.one_int.connect_setitem
        args = (obj, "x")
        kwargs = {"maxargs": 1}
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
            emitter.one_int.connect_setattr(obj, "x", maxargs=1)
    elif callback_type == "setitem":
        for _ in range(n_connections):
            emitter.one_int.connect_setitem(obj, "x", maxargs=1)
    else:
        callback = _get_callback(callback_type, obj)
        for _ in range(n_connections):
            emitter.one_int.connect(callback, unique=False)

    benchmark(emitter.one_int.emit, 1)


@pytest.mark.benchmark
def test_evented_creation() -> None:
    @evented
    @dataclass
    class Obj:
        x: int = 0
        y: str = "hi"
        z: bool = False

    _ = Obj().events  # type: ignore


def test_evented_setattr(benchmark: Callable) -> None:
    @evented
    @dataclass
    class Obj:
        x: int = 0
        y: str = "hi"
        z: bool = False

    obj = Obj()
    _ = obj.events  # type: ignore

    benchmark(setattr, obj, "x", 1)


def _get_dataclass(type_: str) -> type:
    if type_ == "attrs":
        from attrs import define

        @define
        class Foo:
            a: int
            b: str
            c: bool
            d: float
            e: tuple[int, str]
            events: ClassVar = SignalGroupDescriptor()

    elif type_ == "dataclass":

        @dataclass
        class Foo:  # type: ignore [no-redef]
            a: int
            b: str
            c: bool
            d: float
            e: tuple[int, str]
            events: ClassVar = SignalGroupDescriptor()

    elif type_ == "msgspec":
        import msgspec

        class Foo(msgspec.Struct):  # type: ignore [no-redef]
            a: int
            b: str
            c: bool
            d: float
            e: tuple[int, str]
            events: ClassVar = SignalGroupDescriptor()

    elif type_ == "pydantic":
        from pydantic import BaseModel

        class Foo(BaseModel):  # type: ignore [no-redef]
            a: int
            b: str
            c: bool
            d: float
            e: tuple[int, str]
            events: ClassVar = SignalGroupDescriptor()

    return Foo


@pytest.mark.parametrize("type_", ["dataclass", "pydantic", "attrs", "msgspec"])
def test_dataclass_group_create(type_: str, benchmark: Callable) -> None:
    if type_ == "msgspec":
        pytest.importorskip("msgspec")

    Foo = _get_dataclass(type_)
    foo = Foo(a=1, b="hi", c=True, d=1.0, e=(1, "hi"))
    benchmark(getattr, foo, "events")


@pytest.mark.parametrize("type_", ["dataclass", "pydantic", "attrs", "msgspec"])
def test_dataclass_setattr(type_: str, benchmark: Callable) -> None:
    if type_ == "msgspec":
        pytest.importorskip("msgspec")

    Foo = _get_dataclass(type_)
    foo = Foo(a=1, b="hi", c=True, d=1.0, e=(1, "hi"))
    mock = Mock()
    foo.events._psygnal_relay.connect(mock)

    def _doit() -> None:
        foo.a = 2
        foo.b = "hello"
        foo.c = False
        foo.d = 2.0
        foo.e = (2, "hello")

    benchmark(_doit)
    for emitted, attr in zip(
        [(2, 1), ("hello", "hi"), (False, True), (2.0, 1.0), ((2, "hello"), (1, "hi"))],
        "abcde",
    ):
        mock.assert_any_call(EmissionInfo(getattr(foo.events, attr), emitted))
        assert getattr(foo, attr) == emitted[0]
