from unittest.mock import Mock

import pytest

from psygnal.containers._evented_dict import EventedDict


@pytest.fixture
def regular_dict():
    return {"A": 1, "B": 2, "C": 3}


@pytest.fixture
def test_dict(regular_dict):
    """EventedDict without basetype set."""
    test_dict = EventedDict(regular_dict)
    test_dict.events = Mock(wraps=test_dict.events)
    return test_dict


@pytest.mark.parametrize(
    "method_name, args, expected",
    [
        ("__getitem__", ("A",), 1),  # read
        ("__setitem__", ("A", 3), None),  # update
        ("__setitem__", ("D", 3), None),  # add new entry
        ("__delitem__", ("A",), None),  # delete
        ("__len__", (), 3),
        ("__newlike__", ({"A": 1},), {"A": 1}),
        ("copy", (), {"A": 1, "B": 2, "C": 3}),
    ],
)
def test_dict_interface_parity(regular_dict, test_dict, method_name, args, expected):
    """Test that EventedDict interface is equivalent to the builtin dict."""
    test_dict_method = getattr(test_dict, method_name)
    assert test_dict == regular_dict
    if hasattr(regular_dict, method_name):
        regular_dict_method = getattr(regular_dict, method_name)
        assert test_dict_method(*args) == regular_dict_method(*args) == expected
        assert test_dict == regular_dict
    else:
        test_dict_method(*args)  # smoke test


def test_dict_inits():
    a = EventedDict({"A": 1, "B": 2, "C": 3})
    b = EventedDict(A=1, B=2, C=3)
    c = EventedDict({"A": 1}, B=2, C=3)
    assert a == b == c


def test_dict_repr(test_dict):
    assert repr(test_dict) == "EventedDict({'A': 1, 'B': 2, 'C': 3})"


def test_instantiation_without_data():
    """Test that EventedDict can be instantiated without data."""
    test_dict = EventedDict()
    assert isinstance(test_dict, EventedDict)


def test_basetype_enforcement_on_instantiation():
    """EventedDict with basetype set should enforce types on instantiation."""
    with pytest.raises(TypeError):
        test_dict = EventedDict({"A": "not an int"}, basetype=int)
    test_dict = EventedDict({"A": 1})
    assert isinstance(test_dict, EventedDict)


def test_basetype_enforcement_on_set_item():
    """EventedDict with basetype set should enforces types on setitem."""
    test_dict = EventedDict(basetype=int)
    test_dict["A"] = 1
    with pytest.raises(TypeError):
        test_dict["A"] = "not an int"


def test_dict_add_events(test_dict):
    """Test that events are emitted before and after an item is added."""
    test_dict.events.adding.emit = Mock(wraps=test_dict.events.adding.emit)
    test_dict.events.added.emit = Mock(wraps=test_dict.events.added.emit)
    test_dict["D"] = 4
    test_dict.events.adding.emit.assert_called_with("D")
    test_dict.events.added.emit.assert_called_with("D", 4)

    test_dict.events.adding.emit.reset_mock()
    test_dict.events.added.emit.reset_mock()
    test_dict["D"] = 4
    test_dict.events.adding.emit.assert_not_called()
    test_dict.events.added.emit.assert_not_called()


def test_dict_change_events(test_dict):
    """Test that events are emitted when an item in the dictionary is replaced."""
    # events shouldn't be emitted on addition

    test_dict.events.changing.emit = Mock(wraps=test_dict.events.changing.emit)
    test_dict.events.changed.emit = Mock(wraps=test_dict.events.changed.emit)
    test_dict["D"] = 4
    test_dict.events.changing.emit.assert_not_called()
    test_dict.events.changed.emit.assert_not_called()
    test_dict["C"] = 4
    test_dict.events.changing.emit.assert_called_with("C")
    test_dict.events.changed.emit.assert_called_with("C", 3, 4)


def test_dict_remove_events(test_dict):
    """Test that events are emitted before and after an item is removed."""
    test_dict.events.removing.emit = Mock(wraps=test_dict.events.removing.emit)
    test_dict.events.removed.emit = Mock(wraps=test_dict.events.removed.emit)
    test_dict.pop("C")
    test_dict.events.removing.emit.assert_called_with("C")
    test_dict.events.removed.emit.assert_called_with("C", 3)
