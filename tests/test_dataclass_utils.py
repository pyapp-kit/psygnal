from dataclasses import dataclass

import pytest
from attr import define
from pydantic import BaseModel

from psygnal import _dataclass_utils

try:
    from msgspec import Struct
except ImportError:
    Struct = None

VARIANTS = ["dataclass", "attrs_class", "pydantic_model"]
if Struct is not None:
    VARIANTS.append("msgspec_struct")


@pytest.mark.parametrize("frozen", [True, False], ids=["frozen", ""])
@pytest.mark.parametrize("type_", VARIANTS)
def test_dataclass_utils(type_: str, frozen: bool) -> None:
    if type_ == "attrs_class":

        @define(frozen=frozen)  # type: ignore
        class Foo:
            x: int
            y: str = "foo"

    elif type_ == "dataclass":

        @dataclass(frozen=frozen)  # type: ignore
        class Foo:  # type: ignore [no-redef]
            x: int
            y: str = "foo"

    elif type_ == "msgspec_struct":

        class Foo(Struct, frozen=frozen):  # type: ignore [no-redef]
            x: int
            y: str = "foo"

    elif type_ == "pydantic_model":

        class Foo(BaseModel):  # type: ignore [no-redef]
            x: int
            y: str = "foo"

            class Config:
                allow_mutation = not frozen

    for name in VARIANTS:
        is_type = getattr(_dataclass_utils, f"is_{name}")
        assert is_type(Foo) is (name == type_)
        assert is_type(Foo(x=1)) is (name == type_)

    assert list(_dataclass_utils.iter_fields(Foo)) == [("x", int), ("y", str)]

    if type_ == "msgspec_struct" and frozen:
        # not supported until next release of msgspec
        return

    assert _dataclass_utils.is_frozen(Foo) == frozen
