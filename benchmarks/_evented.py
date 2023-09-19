"""This script isn't run by asv... but can be run directly to see how
evented dataclasses compare to non-evented dataclasses."""
import timeit
from dataclasses import dataclass
from typing import ClassVar

try:
    from psygnal import SignalGroupDescriptor
except ImportError:
    SignalGroupDescriptor = None


def _get_dataclass(type_: str, evented: bool) -> type:
    if type_ == "attrs":
        from attrs import define

        @define
        class Foo:
            a: int
            b: str
            c: bool
            d: float
            e: tuple[int, str]
            if evented:
                events: ClassVar = SignalGroupDescriptor()

    elif type_ == "dataclass":

        @dataclass
        class Foo:  # type: ignore [no-redef]
            a: int
            b: str
            c: bool
            d: float
            e: tuple[int, str]
            if evented:
                events: ClassVar = SignalGroupDescriptor()

    elif type_ == "msgspec":
        import msgspec

        class Foo(msgspec.Struct):  # type: ignore [no-redef]
            a: int
            b: str
            c: bool
            d: float
            e: tuple[int, str]
            if evented:
                events: ClassVar = SignalGroupDescriptor()

    elif type_ == "pydantic":
        from pydantic import BaseModel

        class Foo(BaseModel):  # type: ignore [no-redef]
            a: int
            b: str
            c: bool
            d: float
            e: tuple[int, str]
            if evented:
                events: ClassVar = SignalGroupDescriptor()

    return Foo


DCLASSES = ["dataclass", "pydantic", "attrs", "msgspec"]

SETUP = """
obj = {cls}(a=1, b='hi', c=True, d=1.0, e=(1, 'hi'))
getattr(obj, 'events', None)
"""


def attribute_access(num: int = 100_000, repeat: int = 20) -> None:
    statement = "obj.e = (2, 'bye')"
    for type_ in DCLASSES:
        Foo = _get_dataclass(type_, False)
        eFoo = _get_dataclass(type_, True)

        _wo_events = timeit.repeat(
            statement,
            setup=SETUP.format(cls="Foo"),
            globals=locals(),
            number=num,
            repeat=repeat,
        )

        _w_events = timeit.repeat(
            statement,
            setup=SETUP.format(cls="eFoo"),
            globals=locals(),
            number=num,
            repeat=repeat,
        )
        wo_events = min(_wo_events) / num * 1000000
        w_events = min(_w_events) / num * 1000000
        print(f"{type_} (no events): {wo_events:.3f} µs")
        print(f"{type_} (with events): {w_events:.3f} µs")
        print(f"{type_} (with events): {w_events / wo_events:.3f}x slower")


if SignalGroupDescriptor is None:
    print("SignalGroupDescriptor not found, skipping evented benchmarks")
elif __name__ == "__main__":
    attribute_access()
