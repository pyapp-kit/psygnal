from typing import ClassVar
from unittest.mock import Mock

import pytest

from psygnal import SignalGroupDescriptor


@pytest.mark.parametrize("type_", ["dataclass", "pydantic", "attrs", "msgspec"])
def test_descriptor_inherits(type_: str) -> None:
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

        class Base(BaseModel):
            a: int
            events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor()

        class Foo(Base):
            b: str

        class Bar(Foo):
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

        class Base(msgspec.Struct):  # type: ignore
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
    assert set(base.events.signals) == {"a"}
    assert set(foo.events.signals) == {"a", "b"}
    assert set(bar.events.signals) == {"a", "b", "c"}

    mock = Mock()
    foo.events.a.connect(mock)

    base.events.a.emit(1)
    mock.assert_not_called()

    bar.events.a.emit(1)
    mock.assert_not_called()

    foo.events.a.emit(1)
    mock.assert_called_once_with(1)
