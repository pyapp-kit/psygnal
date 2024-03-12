# from __future__ import annotations  # breaks msgspec Annotated

from typing import ClassVar
from unittest.mock import Mock

import pytest

from psygnal import (
    Signal,
    SignalGroup,
    SignalGroupDescriptor,
)


@pytest.mark.parametrize(
    "type_",
    [
        "dataclass",
        "attrs",
        "pydantic",
        "msgspec",
    ],
)
def test_alias_parameters(type_: str) -> None:
    foo_options = {"signal_aliases": {"_b": None}}
    bar_options = {
        "signal_aliases": lambda x: None if x.startswith("_") else f"{x}_changed"
    }
    baz_options = {"signal_aliases": {"a": "a_changed", "_b": "b_changed"}}

    if type_ == "dataclass":
        from dataclasses import dataclass, field

        @dataclass
        class Foo:
            events: ClassVar = SignalGroupDescriptor(**foo_options)
            a: int
            _b: str

        @dataclass
        class Bar:
            events: ClassVar = SignalGroupDescriptor(**bar_options)
            a: int
            _b: str

        @dataclass
        class Baz:
            events: ClassVar = SignalGroupDescriptor(**baz_options)
            a: int
            _b: str = field(default="b")

            @property
            def b(self) -> str:
                return self._b

            @b.setter
            def b(self, value: str):
                self._b = value

    elif type_ == "attrs":
        from attrs import define, field

        @define
        class Foo:
            events: ClassVar = SignalGroupDescriptor(**foo_options)
            a: int
            _b: str = field(alias="_b")

        @define
        class Bar:
            events: ClassVar = SignalGroupDescriptor(**bar_options)
            a: int
            _b: str = field(alias="_b")

        @define
        class Baz:
            events: ClassVar = SignalGroupDescriptor(**baz_options)
            a: int
            _b: str = field(alias="_b", default="b")

            @property
            def b(self) -> str:
                return self._b

            @b.setter
            def b(self, value: str):
                self._b = value

    elif type_ == "pydantic":
        pytest.importorskip("pydantic", minversion="2")
        from pydantic import BaseModel

        class Foo(BaseModel):
            events: ClassVar = SignalGroupDescriptor(**foo_options)
            a: int
            _b: str  # not a field anyway

        class Bar(BaseModel):
            events: ClassVar = SignalGroupDescriptor(**bar_options)
            a: int
            _b: str  # not a field anyway

        class Baz(BaseModel):
            events: ClassVar = SignalGroupDescriptor(**baz_options)
            a: int
            _b: str = "b"  # not defining a field, signal will not be created

            @property
            def b(self) -> str:
                return self._b

            @b.setter
            def b(self, value: str):
                self._b = value

    elif type_ == "msgspec":
        msgspec = pytest.importorskip("msgspec")

        class Foo(msgspec.Struct):  # type: ignore
            events: ClassVar = SignalGroupDescriptor(**foo_options)
            a: int
            _b: str

        class Bar(msgspec.Struct):  # type: ignore
            events: ClassVar = SignalGroupDescriptor(**bar_options)
            a: int
            _b: str

        class Baz(msgspec.Struct):  # type: ignore
            events: ClassVar = SignalGroupDescriptor(**baz_options)
            a: int
            _b: str = "b"

            @property
            def b(self) -> str:
                return self._b

            @b.setter
            def b(self, value: str):
                self._b = value

    # Instantiate objects
    foo = Foo(a=1, _b="b")
    bar = Bar(a=1, _b="b")
    baz = Baz(a=1)

    # Check signals
    assert set(foo.events) == {"a"}
    assert hasattr(foo.events, "_psygnal_aliases")
    assert foo.events._psygnal_aliases == {"a": "a", "_b": None}

    assert set(bar.events) == {"a_changed"}
    assert hasattr(bar.events, "_psygnal_aliases")
    if type_.startswith("pydantic"):
        assert bar.events._psygnal_aliases == {"a": "a_changed"}
    else:
        assert bar.events._psygnal_aliases == {"a": "a_changed", "_b": None}

    if type_.startswith("pydantic"):
        assert set(baz.events) == {"a_changed"}
    else:
        assert set(baz.events) == {"a_changed", "b_changed"}
    assert hasattr(baz.events, "_psygnal_aliases")
    assert baz.events._psygnal_aliases == {
        "a": "a_changed",
        "_b": "b_changed",
    }

    mock = Mock()
    foo.events.a.connect(mock)
    bar.events.a_changed.connect(mock)
    baz.events.a_changed.connect(mock)
    if not type_.startswith("pydantic"):
        baz.events.b_changed.connect(mock)

    # Foo
    foo.a = 1
    mock.assert_not_called()
    foo.a = 2
    mock.assert_called_once_with(2, 1)
    mock.reset_mock()
    foo._b = "b"
    foo._b = "c"
    mock.assert_not_called()

    # Bar
    bar.a = 1
    mock.assert_not_called()
    bar.a = 2
    mock.assert_called_once_with(2, 1)
    mock.reset_mock()
    bar._b = "b"
    bar._b = "c"
    mock.assert_not_called()

    # Baz
    baz.a = 1
    mock.assert_not_called()
    baz.a = 2
    mock.assert_called_once_with(2, 1)
    mock.reset_mock()

    # pydantic v1 does not support properties
    if type_ == "pydantic_v1":
        return

    baz.b = "b"
    mock.assert_not_called()
    baz.b = "c"
    if not type_.startswith("pydantic"):
        mock.assert_called_once_with("c", "b")


@pytest.mark.parametrize("collect", [False, True])
def test_direct_signal_group(collect) -> None:

    class FooSignalGroup(SignalGroup, signal_aliases={"e": None}):
        a = Signal(int, int)
        b_changed = Signal(float, float)
        c = Signal(str, str)
        d = Signal(str, str)
        e = Signal(str, str)

    class Foo:
        events: ClassVar = SignalGroupDescriptor(
            signal_group_class=FooSignalGroup,
            collect_fields=collect,
            signal_aliases={"b": "b_changed", "c": None, "_c": "c"},
        )
        a: int
        b: float
        _c: str
        _d: str

        def __init__(self, a: int = 1, b: float = 2.0, c: str = "c", d: str = "d"):
            self.a = a
            self.b = b
            self.c = c
            self.d = d

        @property
        def c(self) -> str:
            return self._c

        @c.setter
        def c(self, value: str):
            self._c = value

        @property
        def d(self) -> str:
            return self._d.lower()

        @d.setter
        def d(self, value: str):
            self._d = value

    foo = Foo()

    assert hasattr(foo.events, "_psygnal_aliases")
    assert foo.events._psygnal_aliases == {
        'b': 'b_changed',
        '_c': 'c',
        'c': None,
        'e': None,
    }

    mock = Mock()
    foo.events.a.connect(mock)
    foo.events.b_changed.connect(mock)
    foo.events.c.connect(mock)
    foo.events.d.connect(mock)

    foo.events.e.connect(mock)
    foo.events.e.emit("f", "e")
    mock.assert_called_once_with("f", "e")
    mock.reset_mock()

    foo.a = 2
    mock.assert_called_once_with(2, 1)
    mock.reset_mock()

    foo.b = 3.0
    mock.assert_called_once_with(3.0, 2.0)
    mock.reset_mock()

    foo.c = "c"
    mock.assert_not_called()
    foo.c = "cc"
    mock.assert_called_once_with("cc", "c")
    mock.reset_mock()
    foo._c = "ccc"
    mock.assert_called_once_with("ccc", "cc")
    mock.reset_mock()

    foo.d = "D"
    mock.assert_not_called()
    foo.d = "DD"
    mock.assert_called_once_with("dd", "d")
    mock.reset_mock()
