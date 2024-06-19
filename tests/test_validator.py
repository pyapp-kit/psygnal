from dataclasses import dataclass
from typing import Annotated, Any

import pytest

from psygnal import Validator, evented


def test_validator():
    def _is_positive(value: Any) -> int:
        try:
            _value = int(value)
        except (ValueError, TypeError):
            raise ValueError("Value must be an integer") from None
        if not _value > 0:
            raise ValueError("Value must be positive")
        return _value

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
