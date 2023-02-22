from dataclasses import dataclass
from typing import Any, ClassVar
from unittest.mock import Mock, patch

import pytest

from psygnal import SignalGroupDescriptor, _compiled, _group_descriptor


@pytest.mark.parametrize("type_", ["dataclass", "pydantic", "attrs", "msgspec"])
def test_descriptor_inherits(type_: str) -> None:
    if type_ == "dataclass":
        from dataclasses import dataclass

        @dataclass
        class Base:
            a: int
            events: ClassVar = SignalGroupDescriptor()

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
            events: ClassVar = SignalGroupDescriptor()

        class Foo(Base):
            b: str

        class Bar(Foo):
            c: float

    elif type_ == "attrs":
        from attrs import define

        @define
        class Base:
            a: int
            events: ClassVar = SignalGroupDescriptor()

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
            events: ClassVar = SignalGroupDescriptor()

        class Foo(Base):
            b: str

        class Bar(Foo):
            c: float

    assert Bar.events is Base.events

    with patch.object(
        _group_descriptor, "evented_setattr", wraps=_group_descriptor.evented_setattr
    ) as mock_decorator:
        base = Base(a=1)
        foo = Foo(a=1, b="2")
        bar = Bar(a=1, b="2", c=3.0)
        bar2 = Bar(a=1, b="2", c=3.0)

        # the patching of __setattr__ should only happen once
        # and it will happen only on the first access of .events
        mock_decorator.assert_not_called()
        assert set(base.events.signals) == {"a"}
        assert set(foo.events.signals) == {"a", "b"}
        assert set(bar.events.signals) == {"a", "b", "c"}
        assert set(bar2.events.signals) == {"a", "b", "c"}
        if not _compiled:  # can't patch otherwise
            assert mock_decorator.call_count == 1

    mock = Mock()
    foo.events.a.connect(mock)

    # base doesn't affect subclass
    base.events.a.emit(1)
    mock.assert_not_called()

    # subclass doesn't affect superclass
    bar.events.a.emit(1)
    mock.assert_not_called()

    foo.events.a.emit(1)
    mock.assert_called_once_with(1)


@pytest.mark.parametrize("patch_setattr", [True, False])
def test_no_patching(patch_setattr: bool) -> None:
    """Test patch_setattr=False doesn't patch the class"""

    # sourcery skip: extract-duplicate-method
    @dataclass
    class Foo:
        a: int
        _events: ClassVar = SignalGroupDescriptor(patch_setattr=patch_setattr)

    with patch.object(
        _group_descriptor, "evented_setattr", wraps=_group_descriptor.evented_setattr
    ) as mock_decorator:
        foo = Foo(a=1)
        foo._events
        if not _compiled:  # can't patch otherwise
            assert mock_decorator.call_count == int(patch_setattr)

    assert _group_descriptor.is_evented(Foo.__setattr__) == patch_setattr
    mock = Mock()
    foo._events.a.connect(mock)
    foo.a = 2
    if patch_setattr:
        mock.assert_called_once_with(2)
    else:
        mock.assert_not_called()


def test_direct_patching() -> None:
    """Test directly using evented_setattr on a class"""
    mock1 = Mock()

    @dataclass
    class Foo:
        a: int
        _events: ClassVar = SignalGroupDescriptor(patch_setattr=False)

        @_group_descriptor.evented_setattr("_events")
        def __setattr__(self, __name: str, __value: Any) -> None:
            mock1(__name, __value)
            super().__setattr__(__name, __value)

    assert _group_descriptor.is_evented(Foo.__setattr__)

    # patch again ... this should NOT cause a double event emission.
    Foo.__setattr__ = _group_descriptor.evented_setattr("_events", Foo.__setattr__)

    foo = Foo(a=1)
    mock = Mock()
    foo._events.a.connect(mock)
    foo.a = 2
    mock.assert_called_once_with(2)  # confirm no double event emission
    mock1.assert_called_with("a", 2)


def test_no_getattr_on_non_evented_fields() -> None:
    """Make sure that we're not accidentally calling getattr on non-evented fields."""
    a_mock = Mock()
    b_mock = Mock()

    @dataclass
    class Foo:
        a: int
        events: ClassVar = SignalGroupDescriptor()

        @property
        def b(self) -> int:
            b_mock(self._b)
            return self._b

        @b.setter
        def b(self, value: int) -> None:
            self._b = value

    foo = Foo(a=1)
    foo.events.a.connect(a_mock)
    foo.a = 2
    a_mock.assert_called_once_with(2)

    foo.b = 1
    b_mock.assert_not_called()  # getter shouldn't have been called
    assert foo.b == 1
    b_mock.assert_called_once_with(1)  # getter should have been called only once
