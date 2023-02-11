import operator
import sys
from dataclasses import dataclass
from typing import no_type_check
from unittest.mock import Mock

import numpy as np
import pytest

from psygnal import SignalGroup, evented, get_evented_namespace, is_evented
from psygnal._evented_decorator import _SignalGroupDescriptor


@no_type_check
def _check_events(cls, events_ns="events"):
    obj = cls(bar=1, baz="2", qux=np.zeros(3))
    assert is_evented(obj)
    assert is_evented(cls)
    assert get_evented_namespace(cls) == events_ns
    assert isinstance(getattr(cls, events_ns), _SignalGroupDescriptor)

    events = getattr(obj, events_ns)
    assert isinstance(events, SignalGroup)
    assert set(events.signals) == {"bar", "baz", "qux"}

    mock = Mock()
    events.bar.connect(mock)
    assert obj.bar == 1
    obj.bar = 2
    assert obj.bar == 2
    mock.assert_called_once_with(2)

    mock.reset_mock()
    obj.baz = "3"
    mock.assert_not_called()

    mock.reset_mock()
    events.qux.connect(mock)
    obj.qux = np.ones(3)
    mock.assert_called_once()
    assert np.array_equal(obj.qux, np.ones(3))


DCLASS_KWARGS = []
if sys.version_info >= (3, 10):
    DCLASS_KWARGS.extend([{"slots": True}, {"slots": False}])


@pytest.mark.parametrize("kwargs", DCLASS_KWARGS)
def test_native_dataclass(kwargs: dict) -> None:
    @evented(equality_operators={"qux": operator.eq})  # just for test coverage
    @dataclass(**kwargs)
    class Foo:
        bar: int
        baz: str
        qux: np.ndarray

    _check_events(Foo)


@pytest.mark.parametrize("slots", [True, False])
def test_attrs_dataclass(slots: bool) -> None:
    from attrs import define

    @evented
    @define(slots=slots)  # type: ignore
    class Foo:
        bar: int
        baz: str
        qux: np.ndarray

    _check_events(Foo)


class Config:
    arbitrary_types_allowed = True


def test_pydantic_dataclass() -> None:
    from pydantic.dataclasses import dataclass

    @evented
    @dataclass(config=Config)
    class Foo:
        bar: int
        baz: str
        qux: np.ndarray

    _check_events(Foo)


def test_msgspec_struct() -> None:
    msgspec = pytest.importorskip("msgspec")

    @evented
    class Foo(msgspec.Struct):
        bar: int
        baz: str
        qux: np.ndarray

    _check_events(Foo)


def test_pydantic_base_model() -> None:
    from pydantic import BaseModel

    @evented(events_namespace="my_events")
    class Foo(BaseModel):
        bar: int
        baz: str
        qux: np.ndarray

        Config = Config  # type: ignore

    _check_events(Foo, "my_events")


def test_no_signals_warn():
    with pytest.warns(UserWarning, match="No mutable fields found in class"):

        @dataclass
        @evented
        class Foo:
            bar: int


@evented
@dataclass
class FooPicklable:
    bar: int


def test_pickle() -> None:
    """Make sure that evented classes are still picklable."""
    import pickle

    obj = FooPicklable(1)
    obj2 = pickle.loads(pickle.dumps(obj))
    assert obj2.bar == 1


def test_get_namespace():
    @evented(events_namespace="my_events")
    @dataclass
    class Foo:
        x: int

    assert get_evented_namespace(Foo) == "my_events"
    assert is_evented(Foo)
