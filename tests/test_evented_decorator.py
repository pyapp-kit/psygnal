import operator
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, no_type_check
from unittest.mock import Mock

import numpy as np
import pytest

from psygnal import EmissionInfo, Signal, SignalGroup, SignalInstance
from psygnal._group import SignalRelay

try:
    import pydantic.version

    PYDANTIC_V2 = pydantic.version.VERSION.startswith("2")
except ImportError:
    PYDANTIC_V2 = False


from psygnal import (
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
    assert set(events) == {"bar", "baz", "qux"}

    mock = Mock()
    events.bar.connect(mock)
    assert obj.bar == 1
    obj.bar = 2
    assert obj.bar == 2
    mock.assert_called_once_with(2, 1)

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
        class Foo(Base): ...

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
        class Foo(Base): ...

    else:

        class Foo(Base):  # type: ignore [no-redef]
            events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor()

    _check_events(Foo)


if PYDANTIC_V2:
    Config = {"arbitrary_types_allowed": True}
else:

    class Config:
        arbitrary_types_allowed = True


@decorated_or_descriptor
def test_pydantic_dataclass(decorator: bool) -> None:
    pytest.importorskip("pydantic")
    from pydantic.dataclasses import dataclass

    @dataclass(config=Config)
    class Base:
        bar: int
        baz: str
        qux: np.ndarray

    if decorator:

        @evented
        class Foo(Base): ...

    else:

        class Foo(Base):  # type: ignore [no-redef]
            events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor()

    _check_events(Foo)


@decorated_or_descriptor
def test_pydantic_base_model(decorator: bool) -> None:
    pytest.importorskip("pydantic")
    from pydantic import BaseModel

    class Base(BaseModel):
        bar: int
        baz: str
        qux: np.ndarray

        if PYDANTIC_V2:
            model_config = Config
        else:
            Config = Config  # type: ignore

    if decorator:

        @evented(events_namespace="my_events")
        class Foo(Base): ...

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
        class Foo: ...

        _ = Foo().events  # type: ignore

    with pytest.warns(UserWarning, match="No mutable fields found on class"):

        class Foo2:
            events = SignalGroupDescriptor()

        _ = Foo2().events

    @dataclass
    class Foo3:
        events = SignalGroupDescriptor(warn_on_no_fields=False)

    # no warning
    _ = Foo3().events


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


def test_name_conflicts() -> None:
    # https://github.com/pyapp-kit/psygnal/pull/269
    from dataclasses import field

    @evented
    @dataclass
    class Foo:
        name: str
        all: bool = False
        is_uniform: bool = True
        signals: list = field(default_factory=list)

    obj = Foo("foo")
    assert obj.name == "foo"
    with pytest.warns(
        UserWarning, match=r"Names \['all', 'is_uniform', 'signals'\] are reserved"
    ):
        group = obj.events

    assert isinstance(group, SignalGroup)

    assert "name" in group
    assert isinstance(group.name, SignalInstance)
    assert group["name"] is group.name

    assert "is_uniform" in group and isinstance(group["is_uniform"], SignalInstance)
    assert "signals" in group and isinstance(group["signals"], SignalInstance)

    # group.all is always a relay
    assert isinstance(group.all, SignalRelay)

    # getitem returns the signal
    assert "all" in group and isinstance(group["all"], SignalInstance)
    assert not isinstance(group["all"], SignalRelay)

    with pytest.raises(AttributeError):  # it's not writeable
        group.all = SignalRelay({})

    assert group.psygnals_uniform() is False

    @evented
    @dataclass
    class Foo2:
        psygnals_uniform: bool = True

    obj2 = Foo2()
    with pytest.warns(match=r"Name \['psygnals_uniform'\] is reserved"):
        _ = obj2.events

    @dataclass
    class Foo3:
        field: int = 1
        _psygnal_signals: str = "signals"

    with pytest.raises(
        TypeError, match="Fields on an evented class cannot start with '_psygnal'"
    ):
        _ = evented(Foo3)


def test_nesting() -> None:
    from dataclasses import dataclass, field

    @evented
    @dataclass
    class Foo:
        x: int = 1

    @evented
    @dataclass
    class Bar:
        y: int = 2
        foo: Foo = field(default_factory=Foo)

    # @evented(connect_child_events=True)  # could also use this syntax
    @dataclass
    class Baz:
        events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor(
            connect_child_events=True
        )
        z: int = 3
        bar: Bar = field(default_factory=Bar)

    baz = Baz()
    mock = Mock()
    events: SignalGroup = baz.events
    events.all.connect(mock)

    baz.bar.foo.x = 3  # trigger nested event

    # what we expect
    inner_inner_info = EmissionInfo(baz.bar.foo.events.x, (3, 1), None)
    inner_info = EmissionInfo(baz.bar.foo.events.all, (inner_inner_info,), "foo")
    expected = EmissionInfo(baz.bar.events.all, (inner_info,), "bar")
    mock.assert_called_with(expected)

    info: EmissionInfo = mock.call_args[0][0]
    assert info.attr_path() == ("bar", "foo", "x")


def test_signal_relay_partial():
    """Test hash and eq methods on _relay_partial objects"""

    class T(SignalGroup):
        sig = Signal(int)

    t = T()
    a = set()
    a.add(t.all._relay_partial("attr_name"))
    a.add(t.all._relay_partial("attr_name"))
    assert len(a) == 1

    assert t.all._relay_partial("attr_name") in a
