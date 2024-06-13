from dataclasses import dataclass, field
from typing import ClassVar, cast
from unittest.mock import Mock

import pytest

from psygnal import EmissionInfo, SignalGroupDescriptor, evented
from psygnal.containers import EventedDict, EventedList, EventedSet

EL2 = EventedList([10, 20, 30])
EL = EventedList([1, 2, EL2])  # TODO: re-emit events from nested lists
ED: EventedDict[str, int] = EventedDict({"a": 1, "b": 2})
ES = EventedSet({"x", "y", "z"})


@evented
@dataclass
class A:
    x: int = 1


@pytest.fixture
def EventedClass():
    @dataclass
    class M:
        events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor(
            connect_child_events=True
        )
        a: EventedList = field(default_factory=lambda: EL.copy())
        b: EventedDict = field(default_factory=lambda: ED.copy())
        c: EventedSet = field(default_factory=lambda: ES.copy())
        d: A = field(default_factory=A)

    return M


@pytest.mark.parametrize(
    "expr, expect",
    [
        ("m.a[1] = 12", ((1, 2, 12), ("a", "changed"))),
        ("m.a = [0, 2]", (([0, 2], EL), ("a",))),
        ("m.b['a'] = 3", (("a", 1, 3), ("b", "changed"))),
        ("m.b = {'x': 11}", (({"x": 11}, ED), ("b",))),
        ("m.c.add('w')", ((("w",), ()), ("c", "items_changed"))),
        (r"m.c = {1}", (({1}, ES), ("c",))),
        ("m.d.x = 12", ((12, 1), ("d", "x"))),
        ("m.d = {'x': 1}", (({"x": 1}, A(x=1)), ("d",))),
    ],
)
def test_nested_containers(expr, expect, EventedClass):
    m = EventedClass()

    mock = Mock()
    m.events.connect(mock)

    exec(expr)
    info = cast(EmissionInfo, mock.call_args[0][0]).flatten()
    assert (info.args, info.loc) == expect
