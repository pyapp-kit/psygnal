from unittest.mock import Mock, call

import pytest

from psygnal import EmissionInfo, Signal, SignalGroup


class MyGroup(SignalGroup):
    sig1 = Signal(int)
    sig2 = Signal(str)


class MyStrictGroup(SignalGroup, strict=True):
    sig1 = Signal(int)
    sig2 = Signal(int)


def test_signal_group():

    assert not MyGroup.is_uniform()
    group = MyGroup()
    assert not group.is_uniform()
    assert isinstance(group.signals, dict)
    assert group.signals == {"sig1": group.sig1, "sig2": group.sig2}

    assert repr(group) == "<SignalGroup 'MyGroup' with 2 signals>"


def test_uniform_group():
    """In a uniform group, all signals must have the same signature."""

    assert MyStrictGroup.is_uniform()
    group = MyStrictGroup()
    assert group.is_uniform()
    assert isinstance(group.signals, dict)
    assert set(group.signals) == {"sig1", "sig2"}

    with pytest.raises(TypeError) as e:

        class BadGroup(SignalGroup, strict=True):
            sig1 = Signal(str)
            sig2 = Signal(int)

    assert str(e.value).startswith("All Signals in a strict SignalGroup must")


@pytest.mark.parametrize("direct", [True, False])
def test_signal_group_connect(direct: bool):

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


def test_signal_group_connect_no_args():
    """Test that group.connect can take a callback that wants no args"""
    group = MyGroup()
    count = []

    def my_slot() -> None:
        count.append(1)

    group.connect(my_slot)
    group.sig1.emit(1)
    group.sig2.emit("hi")
    assert len(count) == 2


def test_group_blocked():
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

    with group.blocked():
        group.sig1.emit(1)
        assert group.sig1._is_blocked

    assert not group.sig1._is_blocked
    # the blocker should have restored subthings to their previous states
    assert group.sig2._is_blocked

    mock1.assert_not_called()
    mock2.assert_not_called()


def test_group_blocked_exclude():
    """Test that we can exempt certain signals from being blocked."""
    group = MyGroup()

    mock1 = Mock()
    mock2 = Mock()

    group.sig1.connect(mock1)
    group.sig2.connect(mock2)

    with group.blocked(exclude=("sig2",)):
        group.sig1.emit(1)
        group.sig2.emit("hi")
    mock1.assert_not_called()
    mock2.assert_called_once_with("hi")


def test_group_disconnect_single_slot():
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


def test_group_disconnect_all_slots():
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
