from dataclasses import dataclass

import pytest
from attr import define

from psygnal import _dataclass_utils

try:
    from msgspec import Struct
except (ImportError, TypeError):  # type error on python 3.12-dev
    Struct = None  # type: ignore [assignment,misc]

try:
    from pydantic import __version__ as pydantic_version

    PYDANTIC2 = pydantic_version.startswith("2.")
except ImportError:
    PYDANTIC2 = False

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
        pytest.importorskip("pydantic")
        from pydantic import BaseModel

        class Foo(BaseModel):  # type: ignore [no-redef]
            x: int
            y: str = "foo"

            if PYDANTIC2:
                model_config = {"frozen": frozen}

            else:

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
