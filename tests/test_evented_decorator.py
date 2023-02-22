import operator
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, no_type_check
from unittest.mock import Mock

import numpy as np
import pytest

from psygnal import (
    SignalGroup,
    SignalGroupDescriptor,
    evented,
    get_evented_namespace,
    is_evented,
)

decorated_or_descriptor = pytest.mark.parametrize(
    "decorator", [True, False], ids=["decorator", "descriptor"]
)


@no_type_check
def _check_events(cls, events_ns="events"):
    obj = cls(bar=1, baz="2", qux=np.zeros(3))
    assert is_evented(obj)
    assert is_evented(cls)
    assert get_evented_namespace(cls) == events_ns
    assert isinstance(getattr(cls, events_ns), SignalGroupDescriptor)

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


@decorated_or_descriptor
@pytest.mark.parametrize("kwargs", DCLASS_KWARGS)
def test_native_dataclass(decorator: bool, kwargs: dict) -> None:
    @dataclass(**kwargs)
    class Base:
        bar: int
        baz: str
        qux: np.ndarray

    if decorator:

        @evented(equality_operators={"qux": operator.eq})  # just for test coverage
        class Foo(Base):
            ...

    else:

        class Foo(Base):  # type: ignore [no-redef]
            events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor(
                equality_operators={"qux": operator.eq}
            )

    _check_events(Foo)


@decorated_or_descriptor
@pytest.mark.parametrize("slots", [True, False])
def test_attrs_dataclass(decorator: bool, slots: bool) -> None:
    from attrs import define

    @define(slots=slots)  # type: ignore [misc]
    class Base:
        bar: int
        baz: str
        qux: np.ndarray

    if decorator:

        @evented
        class Foo(Base):
            ...

    else:

        class Foo(Base):  # type: ignore [no-redef]
            events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor()

    _check_events(Foo)


class Config:
    arbitrary_types_allowed = True


@decorated_or_descriptor
def test_pydantic_dataclass(decorator: bool) -> None:
    from pydantic.dataclasses import dataclass

    @dataclass(config=Config)
    class Base:
        bar: int
        baz: str
        qux: np.ndarray

    if decorator:

        @evented
        class Foo(Base):
            ...

    else:

        class Foo(Base):  # type: ignore [no-redef]
            events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor()

    _check_events(Foo)


@decorated_or_descriptor
def test_pydantic_base_model(decorator: bool) -> None:
    from pydantic import BaseModel

    class Base(BaseModel):
        bar: int
        baz: str
        qux: np.ndarray

        Config = Config  # type: ignore

    if decorator:

        @evented(events_namespace="my_events")
        class Foo(Base):
            ...

    else:

        class Foo(Base):  # type: ignore [no-redef]
            my_events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor()

    _check_events(Foo, "my_events")


@pytest.mark.parametrize("decorator", [True, False], ids=["decorator", "descriptor"])
def test_msgspec_struct(decorator: bool) -> None:
    if TYPE_CHECKING:
        import msgspec
    else:
        msgspec = pytest.importorskip("msgspec")  # remove when py37 is dropped

    if decorator:

        @evented
        class Foo(msgspec.Struct):
            bar: int
            baz: str
            qux: np.ndarray

    else:

        class Foo(msgspec.Struct):  # type: ignore [no-redef]
            bar: int
            baz: str
            qux: np.ndarray
            events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor()

    _check_events(Foo)


def test_no_signals_warn() -> None:
    with pytest.warns(UserWarning, match="No mutable fields found on class"):

        @evented
        class Foo:
            ...

        Foo().events  # type: ignore

    with pytest.warns(UserWarning, match="No mutable fields found on class"):

        class Foo2:
            events = SignalGroupDescriptor()

        Foo2().events

    @dataclass
    class Foo3:
        events = SignalGroupDescriptor(warn_on_no_fields=False)

    # no warning
    Foo3().events


@dataclass
class FooPicklable:
    bar: int
    events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor(
        cache_on_instance=False
    )


def test_pickle() -> None:
    """Make sure that evented classes are still picklable."""
    import pickle

    obj = FooPicklable(1)
    obj2 = pickle.loads(pickle.dumps(obj))
    assert obj2.bar == 1


def test_get_namespace() -> None:
    @evented(events_namespace="my_events")
    @dataclass
    class Foo:
        x: int

    assert get_evented_namespace(Foo) == "my_events"
    assert is_evented(Foo)
