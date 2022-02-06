from unittest.mock import Mock, call

import pytest

from psygnal import EmissionInfo, Signal, SignalGroup


def test_signal_group():
    class MyGroup(SignalGroup):
        sig1 = Signal(int)
        sig2 = Signal(str)

    assert not MyGroup.is_uniform()
    group = MyGroup()
    assert not group.is_uniform()
    assert isinstance(group.signals, dict)
    assert group.signals == {"sig1": group.sig1, "sig2": group.sig2}


def test_uniform_group():
    """In a uniform group, all signals must have the same signature."""

    class MyGroup(SignalGroup, strict=True):
        sig1 = Signal(int)
        sig2 = Signal(int)

    assert MyGroup.is_uniform()
    group = MyGroup()
    assert group.is_uniform()
    assert isinstance(group.signals, dict)
    assert set(group.signals) == {"sig1", "sig2"}

    with pytest.raises(TypeError) as e:

        class MyGroup2(SignalGroup, strict=True):
            sig1 = Signal(str)
            sig2 = Signal(int)

    assert str(e.value).startswith("All Signals in a strict SignalGroup must")


@pytest.mark.parametrize("direct", [True, False])
def test_signal_group_connect(direct: bool):
    class MyGroup(SignalGroup):
        sig1 = Signal(int)
        sig2 = Signal(str)

    mock = Mock()
    group = MyGroup()
    if direct:
        # the callback wants the emitted arguments directly
        group.connect_direct(mock)
    else:
        # the callback will receive an EmissionInfo tuple
        # (SignalInstance, arg_tuple, extra_info_dict)
        group.connect(mock, extra="something")
    group.sig1.emit(1)
    group.sig2.emit("hi")

    assert mock.call_count == 2
    # if connect_with_info was used, the callback will be given an EmissionInfo
    # tuple that contains the args as well as the signal instance used
    if direct:
        expected_calls = [call(1), call("hi")]
    else:
        expected_calls = [
            call(EmissionInfo(group.sig1, (1,), {"extra": "something"})),
            call(EmissionInfo(group.sig2, ("hi",), {"extra": "something"})),
        ]
    mock.assert_has_calls(expected_calls)
