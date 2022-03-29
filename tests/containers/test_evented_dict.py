from unittest.mock import Mock

import pytest

from psygnal.containers._evented_dict import EventedDict


@pytest.fixture
def regular_dict():
    return {'A': 1, 'B': 2, 'C': 3}


@pytest.fixture
def test_dict(regular_dict):
    evented_dict = EventedDict(regular_dict)
    evented_dict.events = Mock(wraps=evented_dict.events)
    return EventedDict(regular_dict)


@pytest.mark.parametrize(
    "method_name, args, expected",
    [
        ('__getitem__', ("A",), ()),  # read
        ('__setitem__', ("A", 3), ('changed',)),  # update
        ('__setitem__', ("D", 3), ('adding', 'added')),  # add new entry
        ('__delitem__', ("A",), ('removing', 'removed')),  # delete
    ]
)
def test_dict_interface_parity(regular_dict, test_dict, method_name, args, expected):
    """Test that EventedDict interface is equivalent to the builtin dict."""
    test_dict_method = getattr(test_dict, method_name)
    assert test_dict == regular_dict
    if hasattr(regular_dict, method_name):
        regular_dict_method = getattr(regular_dict, method_name)
        assert test_dict_method(*args) == regular_dict_method(*args)
        assert test_dict == regular_dict
    else:
        test_dict_method(*args)  # smoke test
