from __future__ import annotations

from copy import deepcopy
from typing import Callable
from unittest.mock import Mock, call

import pytest

import psygnal

try:
    from typing import Annotated  # py39
except ImportError:
    Annotated = None

from psygnal import EmissionInfo, Signal, SignalGroup, SignalInstance
from psygnal._group import SignalRelay


class MyGroup(SignalGroup):
    sig1 = Signal(int)
    sig2 = Signal(str)


with pytest.warns():

    class ConflictGroup(SignalGroup):
        sig1 = Signal(int)
        connect = Signal(int)  # type: ignore


def test_cannot_instantiate_group() -> None:
    with pytest.raises(TypeError, match="Cannot instantiate `SignalGroup` directly"):
        SignalGroup()


def test_signal_group() -> None:
    assert not MyGroup.psygnals_uniform()
    with pytest.warns(
        FutureWarning, match="The `is_uniform` method on SignalGroup is deprecated"
    ):
        assert not MyGroup.is_uniform()
    group = MyGroup()
    assert not group.psygnals_uniform()
    assert list(group) == ["sig1", "sig2"]  # testing __iter__
    assert group.sig1 is group["sig1"]
    assert set(group.signals) == {"sig1", "sig2"}

    assert repr(group) == "<SignalGroup 'MyGroup' with 2 signals>"


def test_uniform_group() -> None:
    """In a uniform group, all signals must have the same signature."""

    class MyStrictGroup(SignalGroup, strict=True):
        sig1 = Signal(int)
        sig2 = Signal(int)

    assert MyStrictGroup.psygnals_uniform()
    group = MyStrictGroup()
    assert group.psygnals_uniform()
    assert set(group) == {"sig1", "sig2"}

    with pytest.raises(TypeError) as e:

        class BadGroup(SignalGroup, strict=True):
            sig1 = Signal(str)
            sig2 = Signal(int)

    assert str(e.value).startswith("All Signals in a strict SignalGroup must")


@pytest.mark.skipif(Annotated is None, reason="requires typing.Annotated")
def test_nonhashable_args() -> None:
    """Test that non-hashable annotations are allowed in a SignalGroup"""

    class MyGroup(SignalGroup):
        sig1 = Signal(Annotated[int, {"a": 1}])  # type: ignore
        sig2 = Signal(Annotated[float, {"b": 1}])  # type: ignore

    assert not MyGroup.psygnals_uniform()

    with pytest.raises(TypeError):

        class MyGroup2(SignalGroup, strict=True):
            sig1 = Signal(Annotated[int, {"a": 1}])  # type: ignore
            sig2 = Signal(Annotated[float, {"b": 1}])  # type: ignore


@pytest.mark.parametrize("direct", [True, False])
def test_signal_group_connect(direct: bool) -> None:
    mock = Mock()
    group = MyGroup()
    if direct:
        # the callback wants the emitted arguments directly
        group.connect_direct(mock)
    else:
        # the callback will receive an EmissionInfo tuple
        # (SignalInstance, arg_tuple)
        group.connect(mock)
    group.sig1.emit(1)
    group.sig2.emit("hi")

    assert mock.call_count == 2
    # if connect_with_info was used, the callback will be given an EmissionInfo
    # tuple that contains the args as well as the signal instance used
    if direct:
        expected_calls = [call(1), call("hi")]
    else:
        expected_calls = [
            call(EmissionInfo(group.sig1, (1,))),
            call(EmissionInfo(group.sig2, ("hi",))),
        ]
    mock.assert_has_calls(expected_calls)


def test_signal_group_connect_no_args() -> None:
    """Test that group.all.connect can take a callback that wants no args"""
    group = MyGroup()
    count = []

    def my_slot() -> None:
        count.append(1)

    group.connect(my_slot)
    group.sig1.emit(1)
    group.sig2.emit("hi")
    assert len(count) == 2


def test_group_blocked() -> None:
    group = MyGroup()

    mock1 = Mock()
    mock2 = Mock()

    group.connect(mock1)
    group.sig1.connect(mock2)
    group.sig1.emit(1)

    mock1.assert_called_once_with(EmissionInfo(group.sig1, (1,)))
    mock2.assert_called_once_with(1)

    mock1.reset_mock()
    mock2.reset_mock()

    group.sig2.block()
    assert group.sig2._is_blocked

    with group.all.blocked():
        group.sig1.emit(1)
        assert group.sig1._is_blocked

    assert not group.sig1._is_blocked
    # the blocker should have restored subthings to their previous states
    assert group.sig2._is_blocked

    mock1.assert_not_called()
    mock2.assert_not_called()


def test_group_blocked_exclude() -> None:
    """Test that we can exempt certain signals from being blocked."""
    group = MyGroup()

    mock1 = Mock()
    mock2 = Mock()

    group.sig1.connect(mock1)
    group.sig2.connect(mock2)

    with group.all.blocked(exclude=("sig2",)):
        group.sig1.emit(1)
        group.sig2.emit("hi")
    mock1.assert_not_called()
    mock2.assert_called_once_with("hi")


def test_group_disconnect_single_slot() -> None:
    """Test that we can disconnect single slots from groups."""
    group = MyGroup()

    mock1 = Mock()
    mock2 = Mock()

    group.sig1.connect(mock1)
    group.sig2.connect(mock2)

    group.disconnect(mock1)
    group.sig1.emit()
    mock1.assert_not_called()

    group.sig2.emit()
    mock2.assert_called_once()


def test_group_disconnect_all_slots() -> None:
    """Test that we can disconnect all slots from groups."""
    group = MyGroup()

    mock1 = Mock()
    mock2 = Mock()

    group.sig1.connect(mock1)
    group.sig2.connect(mock2)

    group.disconnect()
    group.sig1.emit()
    group.sig2.emit()

    mock1.assert_not_called()
    mock2.assert_not_called()


def test_weakref() -> None:
    """Make sure that the group doesn't keep a strong reference to the instance."""
    import gc

    class T: ...

    obj = T()
    group = MyGroup(obj)
    assert group.all.instance is obj
    del obj
    gc.collect()
    assert group.all.instance is None


@pytest.mark.parametrize(
    "Group, signame, get_sig",
    [
        (MyGroup, "sig1", getattr),
        (MyGroup, "sig1", SignalGroup.__getitem__),
        (ConflictGroup, "sig1", getattr),
        (ConflictGroup, "sig1", SignalGroup.__getitem__),
        (ConflictGroup, "connect", SignalGroup.__getitem__),
    ],
)
def test_group_deepcopy(
    Group: type[SignalGroup], signame: str, get_sig: Callable
) -> None:
    """_summary_

    Parameters
    ----------
    Group : type[SignalGroup]
        The group class to test, where ConflictGroup has a signal named "connect"
        which conflicts with the SignalGroup method of the same name.
    signame : str
        The name of the signal to test
    get_sig : Callable
        The method to use to get the signal instance from the group. we don't
        test getattr for ConflictGroup because it has a signal named "connect"
    """

    class T:
        def method(self) -> None: ...

    obj = T()
    group = Group(obj)
    assert deepcopy(group) is not group  # but no warning

    group.connect(obj.method)
    group2 = deepcopy(group)

    assert not len(group2.all)
    mock = Mock()
    mock2 = Mock()
    group.connect(mock)
    group2.connect(mock2)

    # test that we can access signalinstances (either using getattr or __getitem__)
    siginst1 = get_sig(group, signame)
    siginst2 = get_sig(group2, signame)
    assert isinstance(siginst1, SignalInstance)
    assert isinstance(siginst2, SignalInstance)
    assert siginst1 is not siginst2

    # test that emitting from the deepcopied group doesn't affect the original
    siginst2.emit(1)
    mock.assert_not_called()
    mock2.assert_called_with(EmissionInfo(siginst2, (1,)))

    # test that emitting from the original group doesn't affect the deepcopied one
    mock2.reset_mock()
    siginst1.emit(1)
    mock.assert_called_with(EmissionInfo(siginst1, (1,)))
    mock2.assert_not_called()


def test_group_conflicts() -> None:
    with pytest.warns(UserWarning, match=r"Name \['connect'\] is reserved"):

        class MyGroup(SignalGroup):
            connect = Signal(int)  # type: ignore
            other_signal = Signal(int)

        class SubGroup(MyGroup):
            sig4 = Signal(int)

    assert "connect" in MyGroup._psygnal_signals
    assert "other_signal" in MyGroup._psygnal_signals
    group = MyGroup()
    assert isinstance(group["connect"], SignalInstance)
    assert not isinstance(group.connect, SignalInstance)

    with pytest.raises(
        TypeError,
        match="SignalGroup subclass cannot have attributes starting with '_psygnal'",
    ):

        class MyGroup2(SignalGroup):
            _psygnal_private = 1

    assert group.other_signal.name == "other_signal"
    assert group["connect"].name == "connect"

    subgroup = SubGroup()
    assert subgroup["connect"].name == "connect"
    assert subgroup.other_signal.name == "other_signal"


def test_group_iter() -> None:
    class Group1(SignalGroup):
        sig1 = Signal()
        sig2 = Signal()
        sig3 = Signal()

    # Delete Signal on Group class
    # You should never do that
    del Group1._psygnal_signals["sig1"]

    assert set(Group1._psygnal_signals) == {"sig2", "sig3"}
    assert hasattr(Group1, "sig1")

    g = Group1()

    # Delete Signal on Group instance
    # You should never do that
    del g._psygnal_signals["sig2"]

    assert "sig1" not in g
    assert "sig2" in g
    assert set(g) == {"sig2", "sig3"}

    with pytest.raises(KeyError):
        g["sig1"]

    sig1_t = g.sig1
    assert isinstance(sig1_t, SignalInstance)
    assert sig1_t.name == "sig1"

    sig2 = g["sig2"]
    assert isinstance(sig2, SignalInstance)
    assert sig2.name == "sig2"

    sig2_t = g.sig2
    assert isinstance(sig2_t, SignalInstance)
    assert sig2_t.name == "sig2"

    # Delete SignalInstance
    del g._psygnal_instances["sig3"]

    assert "sig3" not in g
    assert set(g) == {"sig2"}
    with pytest.raises(KeyError):
        g["sig3"]


def test_group_subclass() -> None:
    # Signals are passed to sub-classes
    class Group1(SignalGroup):
        sig1 = Signal()

    class Group2(Group1):
        sig2 = Signal()

    assert "sig1" in Group1._psygnal_signals
    assert "sig1" in Group2._psygnal_signals
    assert "sig2" in Group2._psygnal_signals
    assert "sig2" not in Group1._psygnal_signals

    assert hasattr(Group1, "sig1") and isinstance(Group1.sig1, Signal)
    assert hasattr(Group2, "sig1") and isinstance(Group2.sig1, Signal)
    assert hasattr(Group2, "sig2") and isinstance(Group2.sig2, Signal)
    assert not hasattr(Group1, "sig2")


def test_delayed_relay_connect() -> None:
    group = MyGroup()
    mock = Mock()
    gmock = Mock()
    assert len(group.sig1) == 0

    group.sig1.connect(mock)
    # group relay hasn't been connected to sig1 or sig2 yet
    assert len(group.sig1) == 1
    assert len(group.sig2) == 0

    group.all.connect(gmock)
    # NOW the relay is connected
    assert len(group.sig1) == 2
    assert len(group.sig2) == 1
    method = group.sig1._slots[-1].dereference()
    assert method
    assert method.__name__ == "_slot_relay"

    group.sig1.emit(1)
    mock.assert_called_once_with(1)
    gmock.assert_called_once_with(EmissionInfo(group.sig1, (1,)))

    group.all.disconnect(gmock)
    assert len(group.sig1) == 1
    assert len(group.all) == 0

    mock.reset_mock()
    gmock.reset_mock()
    group.sig1.emit(1)
    mock.assert_called_once_with(1)
    gmock.assert_not_called()


@pytest.mark.skipif(psygnal._compiled, reason="requires uncompiled psygnal")
def test_group_relay_signatures() -> None:
    from inspect import signature

    for name in dir(SignalGroup):
        if (
            hasattr(SignalRelay, name)
            and not name.startswith("_")
            and callable(getattr(SignalRelay, name))
        ):
            group_sig = signature(getattr(SignalGroup, name))
            relay_sig = signature(getattr(SignalRelay, name))

            assert group_sig == relay_sig


def test_group_relay_passthrough() -> None:
    group = MyGroup()

    mock1 = Mock()
    mock2 = Mock()

    # test connection
    group.connect(mock1)
    group.all.connect(mock2)
    group.sig1.emit(1)
    mock1.assert_called_once_with(EmissionInfo(group.sig1, (1,)))
    mock2.assert_called_once_with(EmissionInfo(group.sig1, (1,)))

    mock1.reset_mock()
    mock2.reset_mock()

    # test disconnection
    group.disconnect(mock1)
    group.all.disconnect(mock2)
    group.sig1.emit("hi")

    mock1.assert_not_called()
    mock2.assert_not_called()

    @group.connect(check_nargs=True)  # testing the decorator as well
    def _(x: int) -> None:
        mock1(x)

    group.all.connect(mock2)

    # test blocking
    with group.blocked():
        group.sig1.emit(1)

    mock1.assert_not_called()
    mock2.assert_not_called()

    with group.all.blocked():
        group.sig1.emit(1)

    mock1.assert_not_called()
    mock2.assert_not_called()

    # smoke test the rest
    group.connect_direct(mock1)
    group.block()
    group.unblock()
    group.blocked()
    group.pause()
    group.resume()
    group.paused()
