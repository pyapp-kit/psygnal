from __future__ import annotations

import contextlib
import dataclasses
import sys
from typing import TYPE_CHECKING, Any, Iterator, cast

if TYPE_CHECKING:
    import attrs
    import msgspec
    from pydantic import BaseModel
    from typing_extensions import TypeGuard


class _DataclassParams:
    init: bool
    repr: bool
    eq: bool
    order: bool
    unsafe_hash: bool
    frozen: bool


class AttrsType:
    __attrs_attrs__: tuple[attrs.Attribute, ...]


_DATACLASS_PARAMS = "__dataclass_params__"
with contextlib.suppress(ImportError):
    from dataclasses import _DATACLASS_PARAMS  # type: ignore


class DataClassType:
    __dataclass_params__: _DataclassParams
    __dataclass_fields__: dict[str, dataclasses.Field]


def is_dataclass(cls: type) -> TypeGuard[DataClassType]:
    """Return True if the class is a dataclass."""
    return dataclasses.is_dataclass(cls)


def is_attrs_class(cls: type) -> TypeGuard[type[AttrsType]]:
    """Return True if the class is an attrs class."""
    attr = sys.modules.get("attr", None)
    return attr.has(cls) if attr is not None else False  # type: ignore [no-any-return]


def is_pydantic_model(cls: type) -> TypeGuard[BaseModel]:
    """Return True if the class is a pydantic BaseModel."""
    pydantic = sys.modules.get("pydantic", None)
    return pydantic is not None and issubclass(cls, pydantic.BaseModel)


def is_msgspec_struct(cls: type) -> TypeGuard[msgspec.Struct]:
    """Return True if the class is a `msgspec.Struct`."""
    msgspec = sys.modules.get("msgspec", None)
    return msgspec is not None and issubclass(cls, msgspec.Struct)


def is_frozen(obj: Any) -> bool:
    """Return True if the object is frozen."""
    # sourcery skip: reintroduce-else
    cls = obj if isinstance(obj, type) else type(obj)

    params = cast("_DataclassParams | None", getattr(cls, _DATACLASS_PARAMS, None))
    if params is not None:
        return params.frozen

    # pydantic
    cfg = getattr(cls, "__config__", None)
    if cfg is not None and getattr(cfg, "allow_mutation", None) is False:
        return True

    # attrs
    if getattr(cls.__setattr__, "__name__", None) == "_frozen_setattrs":
        return True

    cfg = getattr(cls, "__struct_config__", None)
    if cfg is not None:
        return bool(getattr(cfg, "frozen", False))

    return False


def iter_fields(
    cls: type, exclude_frozen: bool = True
) -> Iterator[tuple[str, type | None]]:
    """Iterate over all fields in the class, including inherited fields.

    This function recognizes dataclasses, attrs classes, msgspec Structs, and pydantic
    models.

    Parameters
    ----------
    cls : type
        The class to iterate over.
    exclude_frozen : bool, optional
        If True, frozen fields will be excluded. By default True.

    Yields
    ------
    tuple[str, type | None]
        The name and type of each field.
    """
    # generally opting for speed here over public API

    dclass_fields = getattr(cls, "__dataclass_fields__", None)
    if dclass_fields is not None:
        for d_field in dclass_fields.values():
            if d_field._field_type is dataclasses._FIELD:  # type: ignore [attr-defined]
                yield d_field.name, d_field.type
        return

    if is_pydantic_model(cls):
        for p_field in cls.__fields__.values():
            if p_field.field_info.allow_mutation or not exclude_frozen:
                yield p_field.name, p_field.outer_type_
        return

    attrs_fields = getattr(cls, "__attrs_attrs__", None)
    if attrs_fields is not None:
        for a_field in attrs_fields:
            yield a_field.name, a_field.type
        return

    if is_msgspec_struct(cls):
        for m_field in cls.__struct_fields__:
            type_ = cls.__annotations__.get(m_field, None)
            yield m_field, type_
        return
