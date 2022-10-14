from typing import no_type_check
from unittest.mock import Mock

import pytest

from psygnal._evented_decorator import evented


@no_type_check
def _check_events(cls):
    obj = cls(bar=1, baz=2)

    mock = Mock()
    obj.events.bar.connect(mock)
    assert obj.bar == 1
    obj.bar = 2
    assert obj.bar == 2
    mock.assert_called_once_with(2)

    mock.reset_mock()
    obj.baz = 3
    mock.assert_not_called()


@pytest.mark.parametrize("slots", [True, False])
def test_native_dataclass(slots: bool):
    from dataclasses import dataclass

    @evented
    @dataclass(slots=slots)
    class Foo:
        bar: int
        baz: int

    _check_events(Foo)


@pytest.mark.parametrize("slots", [True, False])
def test_attrs_dataclass(slots: bool):
    from attrs import define

    @evented
    @define(slots=slots)
    class Foo:
        bar: int
        baz: int

    _check_events(Foo)


def test_pydantic_dataclass():
    from pydantic.dataclasses import dataclass

    @evented
    @dataclass
    class Foo:
        bar: int
        baz: int

    _check_events(Foo)


def test_pydantic_base_model():
    from pydantic import BaseModel

    @evented
    class Foo(BaseModel):
        bar: int
        baz: int

    _check_events(Foo)
