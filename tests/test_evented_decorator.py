import sys
from typing import no_type_check
from unittest.mock import Mock

import pytest

from psygnal import SignalGroup, evented


@no_type_check
def _check_events(cls):
    obj = cls(bar=1, baz="2")

    assert isinstance(obj.events, SignalGroup)
    assert set(obj.events.signals) == {"bar", "baz"}

    mock = Mock()
    obj.events.bar.connect(mock)
    assert obj.bar == 1
    obj.bar = 2
    assert obj.bar == 2
    mock.assert_called_once_with(2)

    mock.reset_mock()
    obj.baz = "3"
    mock.assert_not_called()


DCLASS_KWARGS = []
if sys.version_info >= (3, 10):
    DCLASS_KWARGS.extend([{"slots": True}, {"slots": False}])


@pytest.mark.parametrize("kwargs", DCLASS_KWARGS)
def test_native_dataclass(kwargs: dict) -> None:
    from dataclasses import dataclass

    @evented
    @dataclass(**kwargs)
    class Foo:
        bar: int
        baz: str

    _check_events(Foo)


@pytest.mark.parametrize("slots", [True, False])
def test_attrs_dataclass(slots: bool) -> None:
    from attrs import define

    @evented
    @define(slots=slots)  # type: ignore
    class Foo:
        bar: int
        baz: str

    _check_events(Foo)


def test_pydantic_dataclass() -> None:
    from pydantic.dataclasses import dataclass

    @evented
    @dataclass
    class Foo:
        bar: int
        baz: str

    _check_events(Foo)


def test_pydantic_base_model() -> None:
    from pydantic import BaseModel

    @evented
    class Foo(BaseModel):
        bar: int
        baz: str

    _check_events(Foo)
