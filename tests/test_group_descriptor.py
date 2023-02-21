from typing import ClassVar

import pytest

from psygnal import SignalGroupDescriptor


@pytest.mark.parametrize("type_", ["dataclass", "pydantic", "attrs", "msgspec"])
def test_descriptor_inherits(type_: str):
    if type_ == "dataclass":
        from dataclasses import dataclass

        @dataclass
        class Base:
            a: int
            events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor()

        @dataclass
        class Foo(Base):
            b: str

        @dataclass
        class Bar(Foo):
            c: float

    elif type_ == "pydantic":
        from pydantic import BaseModel

        class Base(BaseModel):  # type: ignore [no-redef]
            a: int
            events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor()

        class Foo(Base):  # type: ignore [no-redef]
            b: str

        class Bar(Foo):  # type: ignore [no-redef]
            c: float

    elif type_ == "attrs":
        from attrs import define

        @define
        class Base:
            a: int
            events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor()

        @define
        class Foo(Base):
            b: str

        @define
        class Bar(Foo):
            c: float

    elif type_ == "msgspec":
        msgspec = pytest.importorskip("msgspec")

        class Base(msgspec.Struct):
            a: int
            events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor()

        class Foo(Base):
            b: str

        class Bar(Foo):
            c: float

    assert Bar.events is Base.events

    base = Base(a=1)
    foo = Foo(a=1, b="2")
    bar = Bar(a=1, b="2", c=3.0)
    assert set(base.events._signals_) == {"a"}
    assert set(foo.events._signals_) == {"a", "b"}
    assert set(bar.events._signals_) == {"a", "b", "c"}
