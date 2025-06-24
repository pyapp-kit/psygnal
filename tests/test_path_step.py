"""Tests to cover missing lines in path/emission functionality."""

from inspect import Signature

import pytest

from psygnal import EmissionInfo, PathStep, Signal, SignalGroup, SignalInstance


def test_pathstep_validation():
    """Test PathStep validation error conditions."""
    # Test empty PathStep (should fail)
    with pytest.raises(ValueError, match="exactly one of attr, index, or key"):
        PathStep()

    # Test multiple fields set (should fail)
    with pytest.raises(ValueError, match="exactly one of attr, index, or key"):
        PathStep(attr="test", index=1)


def test_pathstep_repr():
    """Test PathStep repr formatting, including long key truncation."""
    # Test attr
    assert repr(PathStep(attr="test")) == ".test"

    # Test index
    assert repr(PathStep(index=5)) == "[5]"

    # Test short key
    assert repr(PathStep(key="short")) == "['short']"

    # Test long key truncation
    class CrazyHashable:
        """A class with a long __repr__."""

        def __repr__(self):
            return "a" * 100

    ps = PathStep(key=CrazyHashable())
    result = repr(ps)
    assert "..." in result
    assert len(result) <= 25  # should be truncated


def test_emission_info_path_validation():
    """Test EmissionInfo path validation."""
    # Create a SignalInstance properly
    instance = SignalInstance(Signature())

    # Valid paths should work
    EmissionInfo(instance, (1,), (PathStep(attr="test"),))
    EmissionInfo(instance, (1,), (PathStep(index=0), PathStep(key="key")))

    # Invalid path types should fail
    with pytest.raises(TypeError):
        EmissionInfo(instance, (1,), (object(),))  # type: ignore


def test_signal_relay_no_emitter():
    """Test SignalRelay when no current emitter."""

    class TestGroup(SignalGroup):
        test_signal = Signal(int)

    group = TestGroup()

    # Test that _slot_relay returns early when no current emitter
    # This should not raise an error and should not emit anything
    relay = group.all
    relay._slot_relay(1, 2, 3)  # Should return early due to no emitter


def test_signal_group_repr_without_instance():
    """Test SignalGroup repr when instance is None."""

    class TestGroup(SignalGroup):
        test_signal = Signal(int)

    # Create group without instance
    group = TestGroup()
    repr_str = repr(group)
    assert "TestGroup" in repr_str
    assert "instance at" not in repr_str  # Should not have instance info


def test_signal_group_repr_with_instance():
    """Test SignalGroup repr when instance is not None."""

    class TestGroup(SignalGroup):
        test_signal = Signal(int)

    class TestObj:
        def __init__(self):
            self.events = TestGroup(instance=self)

    # Create group with instance
    obj = TestObj()
    repr_str = repr(obj.events)
    assert "TestGroup" in repr_str
    assert "instance at" in repr_str  # Should have instance info
    assert "TestObj" in repr_str


def test_list_signal_instance_relocate_empty_args():
    """Test ListSignalInstance _psygnal_relocate_info_ with empty args."""
    from psygnal.containers._evented_list import ListSignalInstance

    # Create a signal instance
    list_sig = ListSignalInstance((int,))

    # Test with empty args
    info = EmissionInfo(list_sig, ())
    result = list_sig._psygnal_relocate_info_(info)
    assert result is info  # Should return unchanged


def test_dict_signal_instance_relocate_empty_args():
    """Test DictSignalInstance _psygnal_relocate_info_ with empty args."""
    from psygnal.containers._evented_dict import DictSignalInstance

    # Create a signal instance
    dict_sig = DictSignalInstance((str,))

    # Test with empty args
    info = EmissionInfo(dict_sig, ())
    result = dict_sig._psygnal_relocate_info_(info)
    assert result is info  # Should return unchanged
