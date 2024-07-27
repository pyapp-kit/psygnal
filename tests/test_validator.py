from dataclasses import dataclass
from typing import Annotated, Any

import pytest

from psygnal import Validator, evented


def _is_positive(value: Any) -> int:
    try:
        _value = int(value)
    except (ValueError, TypeError):
        raise ValueError("Value must be an integer") from None
    if not _value > 0:
        raise ValueError("Value must be positive")
    return _value


def test_validator():
    @evented
    @dataclass
    class Foo:
        x: Annotated[int, Validator(_is_positive)]

    with pytest.raises(ValueError, match="Value must be positive"):
        Foo(x=-1)
    foo = Foo(x="1")  # type: ignore
    assert isinstance(foo.x, int)
    with pytest.raises(ValueError):
        foo.x = -1


def test_validator_resolution():
    @evented
    @dataclass
    class Bar:
        x: "Annotated[int, Validator(_is_positive)]"

    with pytest.raises(ValueError, match="Value must be positive"):
        Bar(x=-1)

    def _local_func(value: Any) -> Any:
        return value

    with pytest.warns(UserWarning, match="Unable to resolve type"):

        @evented
        @dataclass
        class Baz:
            x: "Annotated[int, Validator(_local_func)]"
