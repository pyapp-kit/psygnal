from __future__ import annotations

import contextlib
import dataclasses
import sys
import types
from dataclasses import dataclass, fields
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterator,
    List,
    Mapping,
    Protocol,
    cast,
    overload,
)

if TYPE_CHECKING:
    from dataclasses import Field

    import attrs
    import msgspec
    from pydantic import BaseModel
    from typing_extensions import TypeAlias, TypeGuard  # py310

    EqOperator: TypeAlias = Callable[[Any, Any], bool]

PSYGNAL_METADATA = "__psygnal_metadata"


class _DataclassParams(Protocol):
    init: bool
    repr: bool
    eq: bool
    order: bool
    unsafe_hash: bool
    frozen: bool


GenericAlias = getattr(types, "GenericAlias", type(List[int]))  # safe for < py 3.9


class AttrsType:
    __attrs_attrs__: tuple[attrs.Attribute, ...]


KW_ONLY = object()
with contextlib.suppress(ImportError):
    from dataclasses import KW_ONLY  # py310
_DATACLASS_PARAMS = "__dataclass_params__"
_DATACLASS_FIELDS = "__dataclass_fields__"


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
    return attr.has(cls) if attr is not None else False  # type: ignore [no-any-return]


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
                if p_field.field_info.allow_mutation or not exclude_frozen:  # type: ignore [attr-defined]
                    yield p_field.name, p_field.outer_type_  # type: ignore [attr-defined]
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


@dataclass
class FieldOptions:
    name: str
    type_: type | None = None
    # set KW_ONLY value for compatibility with python < 3.10
    _: KW_ONLY = KW_ONLY  # type: ignore [valid-type]
    alias: str | None = None
    skip: bool | None = None
    eq: EqOperator | None = None
    disable_setattr: bool | None = None


def is_kw_only(f: Field) -> bool:
    if hasattr(f, "kw_only"):
        return cast(bool, f.kw_only)
    # for python < 3.10
    if f.name not in ["name", "type_"]:
        return True
    return False


def sanitize_field_options_dict(d: Mapping) -> dict[str, Any]:
    field_options_kws = [f.name for f in fields(FieldOptions) if is_kw_only(f)]
    return {k: v for k, v in d.items() if k in field_options_kws}


def get_msgspec_metadata(
    cls: type[msgspec.Struct],
    m_field: str,
) -> tuple[type | None, dict[str, Any]]:
    # Look for type in cls and super classes
    type_: type | None = None
    for super_cls in cls.__mro__:
        if not hasattr(super_cls, "__annotations__"):
            continue
        type_ = super_cls.__annotations__.get(m_field, None)
        if type_ is not None:
            break

    msgspec = sys.modules.get("msgspec", None)
    if msgspec is None:
        return type_, {}

    metadata_list = getattr(type_, "__metadata__", [])

    metadata: dict[str, Any] = {}
    for meta in metadata_list:
        if not isinstance(meta, msgspec.Meta):
            continue
        single_meta: dict[str, Any] = getattr(meta, "extra", {}).get(
            PSYGNAL_METADATA, {}
        )
        metadata.update(single_meta)

    return type_, metadata


def iter_fields_with_options(
    cls: type, exclude_frozen: bool = True
) -> Iterator[FieldOptions]:
    """Iterate over all fields in the class, return a field description.

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
    FieldOptions
        A dataclass instance with the name, type and metadata of each field.
    """
    # Add metadata for dataclasses.dataclass
    dclass_fields = getattr(cls, "__dataclass_fields__", None)
    if dclass_fields is not None:
        """
        Example
        -------
        from dataclasses import dataclass, field


        @dataclass
        class Foo:
           bar: int = field(metadata={"alias": "bar_alias"})

        assert (
            Foo.__dataclass_fields__["bar"].metadata ==
            {"__psygnal_metadata": {"alias": "bar_alias"}}
        )

        """
        for d_field in dclass_fields.values():
            if d_field._field_type is dataclasses._FIELD:  # type: ignore [attr-defined]
                metadata = getattr(d_field, "metadata", {}).get(PSYGNAL_METADATA, {})
                metadata = sanitize_field_options_dict(metadata)
                options = FieldOptions(d_field.name, d_field.type, **metadata)
                yield options
        return

    # Add metadata for pydantic dataclass
    if is_pydantic_model(cls):
        """
        Example
        -------
        from typing import Annotated

        from pydantic import BaseModel, Field


        # Only works with Pydantic v2
        class Foo(BaseModel):
            bar: Annotated[
                str,
                {'__psygnal_metadata': {"alias": "bar_alias"}}
            ] = Field(...)

        # Working with Pydantic v2 and partially with v1
        # Alternative, using Field `json_schema_extra` keyword argument
        class Bar(BaseModel):
            bar: str = Field(
                json_schema_extra={PSYGNAL_METADATA: {"alias": "bar_alias"}}
            )


        assert (
            Foo.model_fields["bar"].metadata[0] ==
            {"__psygnal_metadata": {"alias": "bar_alias"}}
        )
        assert (
            Bar.model_fields["bar"].json_schema_extra ==
            {"__psygnal_metadata": {"alias": "bar_alias"}}
        )

        """
        if hasattr(cls, "model_fields"):
            # Pydantic v2
            for field_name, p_field in cls.model_fields.items():
                # skip frozen field
                if exclude_frozen and p_field.frozen:
                    continue
                metadata_list = getattr(p_field, "metadata", [])
                metadata = {}
                for field in metadata_list:
                    metadata.update(field.get(PSYGNAL_METADATA, {}))
                # Compat with using Field `json_schema_extra` keyword argument
                if isinstance(getattr(p_field, "json_schema_extra", None), Mapping):
                    meta_dict = cast(Mapping, p_field.json_schema_extra)
                    metadata.update(meta_dict.get(PSYGNAL_METADATA, {}))
                metadata = sanitize_field_options_dict(metadata)
                options = FieldOptions(field_name, p_field.annotation, **metadata)
                yield options
            return

        else:
            # Pydantic v1, metadata is not always working
            for pv1_field in cls.__fields__.values():  # type: ignore [attr-defined]
                # skip frozen field
                if exclude_frozen and not pv1_field.field_info.allow_mutation:
                    continue
                meta_dict = getattr(pv1_field.field_info, "extra", {}).get(
                    "json_schema_extra", {}
                )
                metadata = meta_dict.get(PSYGNAL_METADATA, {})

                metadata = sanitize_field_options_dict(metadata)
                options = FieldOptions(
                    pv1_field.name,
                    pv1_field.outer_type_,
                    **metadata,
                )
                yield options
            return

    # Add metadata for attrs dataclass
    attrs_fields = getattr(cls, "__attrs_attrs__", None)
    if attrs_fields is not None:
        """
        Example
        -------
        from attrs import define, field


        @define
        class Foo:
           bar: int = field(metadata={"alias": "bar_alias"})

        assert (
            Foo.__attrs_attrs__.bar.metadata ==
            {"__psygnal_metadata": {"alias": "bar_alias"}}
        )

        """
        for a_field in attrs_fields:
            metadata = getattr(a_field, "metadata", {}).get(PSYGNAL_METADATA, {})
            metadata = sanitize_field_options_dict(metadata)
            options = FieldOptions(a_field.name, a_field.type, **metadata)
            yield options
        return

    # Add metadata for attrs dataclass
    if is_msgspec_struct(cls):
        """
        Example
        -------
        from typing import Annotated

        from msgspec import Meta, Struct


        class Foo(Struct):
            bar: Annotated[
                str,
                Meta(extra={"__psygnal_metadata": {"alias": "bar_alias"}))
            ] = ""


        print(Foo.__annotations__["bar"].__metadata__[0].extra)
        # {"__psygnal_metadata": {"alias": "bar_alias"}}

        """
        for m_field in cls.__struct_fields__:
            try:
                type_, metadata = get_msgspec_metadata(cls, m_field)
                metadata = sanitize_field_options_dict(metadata)
            except AttributeError:
                msg = f"Cannot parse field metadata for {m_field}: {type_}"
                # logger.exception(msg)
                print(msg)
                type_, metadata = None, {}
            options = FieldOptions(m_field, type_, **metadata)
            yield options
        return
