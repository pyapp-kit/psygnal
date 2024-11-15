# from __future__ import annotations  # breaks msgspec Annotated

import contextlib
import sys
from typing import ClassVar, Dict, Optional
from unittest.mock import Mock

import pytest

from psygnal import (
    PSYGNAL_METADATA,
    EmissionInfo,
    SignalGroupDescriptor,
    is_evented,
)

Annotated = None
with contextlib.suppress(ImportError):
    from typing import Annotated  # type: ignore


min_py_version = pytest.mark.skipif(
    sys.version_info < (3, 9), reason="needs typing.Annotated"
)


def get_signal_aliases(obj: object) -> Dict[str, Optional[str]]:
    if not is_evented(obj):
        return {}
    return obj.events._psygnal_aliases


@pytest.mark.parametrize(
    "type_",
    [
        "dataclass",
        "attrs",
        pytest.param("pydantic", marks=min_py_version),
        pytest.param("msgspec", marks=min_py_version),
    ],
)
def test_field_metadata(type_: str) -> None:
    a_metadata = {PSYGNAL_METADATA: {"alias": "a_changed"}}
    b_metadata = {PSYGNAL_METADATA: {"eq": lambda s1, s2: s1.lower() == s2.lower()}}
    c_metadata = {PSYGNAL_METADATA: {"skip": True}}
    d_metadata = {PSYGNAL_METADATA: {"disable_setattr": True}}

    if type_ == "dataclass":
        from dataclasses import dataclass, field

        @dataclass
        class Base:
            a: int = field(metadata=a_metadata)
            events: ClassVar = SignalGroupDescriptor()

        @dataclass
        class Foo(Base):
            b: str = field(metadata=b_metadata)

        @dataclass
        class Bar(Foo):
            c: float = field(metadata=c_metadata)

        @dataclass
        class Baz(Bar):
            d: float = field(metadata=d_metadata)

    elif type_ == "attrs":
        from attrs import define, field

        @define
        class Base:
            a: int = field(metadata=a_metadata)
            events: ClassVar = SignalGroupDescriptor()

        @define
        class Foo(Base):
            b: str = field(metadata=b_metadata)

        @define
        class Bar(Foo):
            c: float = field(metadata=c_metadata)

        @define
        class Baz(Bar):
            d: float = field(metadata=d_metadata)

    elif type_ == "pydantic":
        pytest.importorskip("pydantic", minversion="2")
        from pydantic import BaseModel, Field

        class Base(BaseModel):
            a: Annotated[int, a_metadata]
            events: ClassVar = SignalGroupDescriptor()

        # Alternative, using Field `json_schema_extra` keyword argument
        class Foo(Base):
            b: str = Field(json_schema_extra=b_metadata)

        class Bar(Foo):
            c: Annotated[float, c_metadata]

        class Baz(Bar):
            d: Annotated[float, d_metadata]

    elif type_ == "msgspec":
        msgspec = pytest.importorskip("msgspec")

        class Base(msgspec.Struct):  # type: ignore
            a: Annotated[int, msgspec.Meta(extra=a_metadata)]
            events: ClassVar = SignalGroupDescriptor()

        class Foo(Base):
            b: Annotated[str, msgspec.Meta(extra=b_metadata)]

        class Bar(Foo):
            c: Annotated[float, msgspec.Meta(extra=c_metadata)]

        class Baz(Bar):
            d: Annotated[float, msgspec.Meta(extra=d_metadata)]

    assert Bar.events is Base.events

    # Instantiate objects
    base = Base(a=1)
    foo = Foo(a=1, b="b")
    bar = Bar(a=1, b="b", c=3.0)
    bar2 = Bar(a=1, b="b", c=3.0)
    baz = Baz(a=1, b="b", c=3.0, d=4.0)

    # the patching of __setattr__ should only happen once
    # and it will happen only on the first access of .events
    assert set(base.events) == {"a_changed"}
    assert set(foo.events) == {"a_changed", "b"}
    assert set(bar.events) == {"a_changed", "b"}
    assert set(bar2.events) == {"a_changed", "b"}
    assert set(baz.events) == {"a_changed", "b", "d"}

    assert get_signal_aliases(base) == {"a": "a_changed"}
    assert get_signal_aliases(foo) == {"a": "a_changed"}
    assert get_signal_aliases(bar) == {"a": "a_changed"}
    assert get_signal_aliases(bar2) == {"a": "a_changed"}
    assert get_signal_aliases(baz) == {"a": "a_changed", "d": None}

    mock = Mock()
    assert not hasattr(foo.events, "a")
    foo.events.a_changed.connect(mock)
    foo.events.b.connect(mock)
    baz.events.a_changed.connect(mock)
    baz.events.b.connect(mock)
    baz.events.d.connect(mock)

    # base doesn't affect subclass
    assert not hasattr(base.events, "a")
    base.events.a_changed.emit(1)
    mock.assert_not_called()

    base.events.a_changed.emit(2)
    mock.assert_not_called()

    # `alias` works
    assert hasattr(foo.events, "a_changed")
    foo.a = 2
    mock.assert_called_once_with(2, 1)
    mock.reset_mock()

    baz.a = 2
    mock.assert_called_once_with(2, 1)
    mock.reset_mock()

    # `eq` works
    foo.b = "B"
    mock.assert_not_called()
    baz.b = "B"
    mock.assert_not_called()

    foo.b = "C"
    mock.assert_called_once_with("C", "B")
    mock.reset_mock()

    # `skip` works
    assert not hasattr(baz.events, "c")

    # `disable_setattr` works
    baz.d = 5.0
    mock.assert_not_called()

    # Check all
    mock1 = Mock()
    baz.events.all.connect(mock1)
    baz.c = 4.0
    mock1.assert_not_called()
    baz.d = 6.0
    mock1.assert_not_called()
    baz.a = 3
    assert hasattr(baz.events, "a_changed")
    mock1.assert_called_once_with(EmissionInfo(baz.events.a_changed, (3, 2)))
