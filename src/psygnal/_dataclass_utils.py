from __future__ import annotations

import contextlib
import dataclasses
import sys
from types import GenericAlias
from typing import TYPE_CHECKING, Any, Protocol, cast, overload

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import TypeGuard

    import attrs
    import msgspec
    from pydantic import BaseModel


class _DataclassParams(Protocol):
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
_DATACLASS_FIELDS = "__dataclass_fields__"
with contextlib.suppress(ImportError):
    from dataclasses import _DATACLASS_FIELDS  # type: ignore


class DataClassType:
    __dataclass_params__: _DataclassParams
    __dataclass_fields__: dict[str, dataclasses.Field]


@overload
def is_dataclass(obj: type) -> TypeGuard[type[DataClassType]]: ...


@overload
def is_dataclass(obj: object) -> TypeGuard[DataClassType]: ...


def is_dataclass(obj: object) -> TypeGuard[DataClassType]:
    """Return True if the object is a dataclass."""
    cls = (
        obj
        if isinstance(obj, type) and not isinstance(obj, GenericAlias)
        else type(obj)
    )
    return hasattr(cls, _DATACLASS_FIELDS)


@overload
def is_attrs_class(obj: type) -> TypeGuard[type[AttrsType]]: ...


@overload
def is_attrs_class(obj: object) -> TypeGuard[AttrsType]: ...


def is_attrs_class(obj: object) -> TypeGuard[type[AttrsType]]:
    """Return True if the class is an attrs class."""
    attr = sys.modules.get("attr", None)
    cls = obj if isinstance(obj, type) else type(obj)
    return attr.has(cls) if attr is not None else False


@overload
def is_pydantic_model(obj: type) -> TypeGuard[type[BaseModel]]: ...


@overload
def is_pydantic_model(obj: object) -> TypeGuard[BaseModel]: ...


def is_pydantic_model(obj: object) -> TypeGuard[BaseModel]:
    """Return True if the class is a pydantic BaseModel."""
    pydantic = sys.modules.get("pydantic", None)
    cls = obj if isinstance(obj, type) else type(obj)
    return pydantic is not None and issubclass(cls, pydantic.BaseModel)


@overload
def is_msgspec_struct(obj: type) -> TypeGuard[type[msgspec.Struct]]: ...


@overload
def is_msgspec_struct(obj: object) -> TypeGuard[msgspec.Struct]: ...


def is_msgspec_struct(obj: object) -> TypeGuard[msgspec.Struct]:
    """Return True if the class is a `msgspec.Struct`."""
    msgspec = sys.modules.get("msgspec", None)
    cls = obj if isinstance(obj, type) else type(obj)
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

    # pydantic v2
    cfg = getattr(cls, "model_config", None)
    if cfg is not None and cfg.get("frozen"):
        return True

    # attrs
    if getattr(cls.__setattr__, "__name__", None) == "_frozen_setattrs":
        return True

    cfg = getattr(cls, "__struct_config__", None)
    if cfg is not None:  # pragma: no cover
        # this will be covered in msgspec > 0.13.1
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

    if (dclass_fields := getattr(cls, "__dataclass_fields__", None)) is not None:
        for d_field in dclass_fields.values():
            if d_field._field_type is dataclasses._FIELD:  # type: ignore [attr-defined]
                yield d_field.name, d_field.type
        return

    if is_pydantic_model(cls):
        if hasattr(cls, "model_fields"):
            for field_name, p_field in cls.model_fields.items():
                if not p_field.frozen or not exclude_frozen:
                    yield field_name, p_field.annotation
        else:
            for p_field in cls.__fields__.values():  # type: ignore [attr-defined]
                if p_field.field_info.allow_mutation or not exclude_frozen:
                    yield p_field.name, p_field.outer_type_
        return

    if (attrs_fields := getattr(cls, "__attrs_attrs__", None)) is not None:
        for a_field in attrs_fields:
            yield a_field.name, a_field.type
        return

    if is_msgspec_struct(cls):
        for m_field in cls.__struct_fields__:
            type_ = cls.__annotations__.get(m_field, None)
            yield m_field, type_
        return
