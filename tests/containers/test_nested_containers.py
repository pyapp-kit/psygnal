from dataclasses import dataclass, field
from typing import ClassVar, cast
from unittest.mock import Mock

import pytest

from psygnal import EmissionInfo, PathStep, SignalGroupDescriptor, evented
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
        # list element reassignment
        ("m.a[1] = 12", ((1, 2, 12), (PathStep(attr="a"), PathStep(index=1)))),
        # list attribute replaced wholesale
        ("m.a = [0, 2]", (([0, 2], EL), (PathStep(attr="a"),))),
        # dict item updated
        ("m.b['a'] = 3", (("a", 1, 3), (PathStep(attr="b"), PathStep(key="a")))),
        # dataclass attribute replaced
        ("m.b = {'x': 11}", (({"x": 11}, ED), (PathStep(attr="b"),))),
        # set mutated
        ("m.c.add('w')", ((("w",), ()), (PathStep(attr="c"),))),
        # set attribute replaced wholesale
        (r"m.c = {1}", (({1}, ES), (PathStep(attr="c"),))),
        # nested dataclass field change
        ("m.d.x = 12", ((12, 1), (PathStep(attr="d"), PathStep(attr="x")))),
        # dataclass attribute replaced wholesale
        ("m.d = {'x': 1}", (({"x": 1}, A(x=1)), (PathStep(attr="d"),))),
        # evented object replaced with another evented object
        ("m.d = A(x=99)", ((A(x=99), A(x=1)), (PathStep(attr="d"),))),
    ],
)
def test_nested_containers(expr, expect, EventedClass):
    m = EventedClass()

    mock = Mock()
    m.events.connect(mock)

    exec(expr)
    info = cast("EmissionInfo", mock.call_args[0][0])
    assert (info.args, info.path) == expect
