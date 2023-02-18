from __future__ import annotations

import contextlib
import operator
import sys
import warnings
import weakref
from dataclasses import fields, is_dataclass
from functools import lru_cache
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Iterator,
    Type,
    TypeVar,
    cast,
    overload,
)

from ._group import SignalGroup
from ._signal import Signal

if TYPE_CHECKING:
    import msgspec
    from pydantic import BaseModel
    from typing_extensions import TypeGuard

    from ._signal import SignalInstance


__all__ = ["is_evented", "get_evented_namespace", "SignalGroupDescriptor"]
_DATACLASS_PARAMS = "__dataclass_params__"
with contextlib.suppress(ImportError):
    from dataclasses import _DATACLASS_PARAMS  # type: ignore

T = TypeVar("T", bound=Type)
S = TypeVar("S")

EqOperator = Callable[[Any, Any], bool]
_EQ_OPERATORS: dict[type, dict[str, EqOperator]] = {}
_EQ_OPERATOR_NAME = "__eq_operators__"
PSYGNAL_GROUP_NAME = "_psygnal_group_"
_NULL = object()


def _get_eq_operator_map(cls: type) -> dict[str, EqOperator]:
    """Return the map of field_name -> equality operator for the class."""
    # if the class has an __eq_operators__ attribute, we use it
    # otherwise use/create the entry for `cls` in the global _EQ_OPERATORS map
    if hasattr(cls, _EQ_OPERATOR_NAME):
        return cast(dict, getattr(cls, _EQ_OPERATOR_NAME))
    else:
        return _EQ_OPERATORS.setdefault(cls, {})


def _check_field_equality(
    cls: type, name: str, before: Any, after: Any, _fail: bool = False
) -> bool:
    """Test if two values are equal for a given field.

    This function will look for a field-specific operator in the the `__eq_operators__`
    attribute of the class if present, otherwise it will use the default equality
    operator for the type.

    Parameters
    ----------
    cls : type
        The class that contains the field.
    name : str
        The name of the field.
    before : Any
        The value of the field before the change.
    after : Any
        The value of the field after the change.
    _fail : bool, optional
        If True, raise a ValueError if the field is not found in the class.
        by default False

    Returns
    -------
    bool
        True if the values are equal, False otherwise.
    """
    if before is _NULL:
        return after is _NULL

    eq_map = _get_eq_operator_map(cls)

    # get and execute the equality operator for the field
    are_equal = eq_map.setdefault(name, operator.eq)
    try:
        # may fail depending on the __eq__ method for the type
        return bool(are_equal(after, before))
    except Exception:
        if _fail:
            raise  # pragma: no cover

        # if we fail, we try to pick a new equality operator
        # if it's a numpy array, we use np.array_equal
        # finally, fallback to operator.is_
        np = sys.modules.get("numpy", None)
        if (
            hasattr(after, "__array__")
            and np is not None
            and are_equal is not np.array_equal
        ):
            eq_map[name] = np.array_equal
            return _check_field_equality(cls, name, before, after, _fail=False)
        else:
            eq_map[name] = operator.is_
            return _check_field_equality(cls, name, before, after, _fail=True)


def _get_eq_op(owner: type, field_name: str) -> EqOperator:
    eq_map = _get_eq_operator_map(owner)
    are_equal = operator.eq

    def eq_op(before: Any, after: Any, _fail: bool = False) -> bool:
        nonlocal are_equal
        try:
            # may fail depending on the __eq__ method for the type
            return bool(are_equal(after, before))
        except Exception:
            if _fail:
                raise  # pragma: no cover

            # if we fail, we try to pick a new equality operator
            # if it's a numpy array, we use np.array_equal
            # finally, fallback to operator.is_
            np = sys.modules.get("numpy", None)
            if (
                hasattr(after, "__array__")
                and np is not None
                and are_equal is not np.array_equal
            ):
                are_equal = np.array_equal  # update the operator
                eq_map[field_name] = np.array_equal  # update the map
                return eq_op(before, after, _fail=False)
            else:
                are_equal = operator.is_  # update the operator
                eq_map[field_name] = operator.is_  # update the map
                return eq_op(before, after, _fail=True)

    eq_map[field_name] = eq_op
    return eq_op


def is_attrs_class(cls: type) -> bool:
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


def iter_fields(cls: type) -> Iterator[tuple[str, type]]:
    """Iterate over all mutable fields in the class, including inherited fields.

    This function recognizes dataclasses, attrs classes, msgspec Structs, and pydantic
    models.
    """
    if is_dataclass(cls):
        if getattr(cls, _DATACLASS_PARAMS).frozen:  # pragma: no cover
            raise TypeError("Frozen dataclasses cannot be made evented.")

        for d_field in fields(cls):
            yield d_field.name, d_field.type

    elif is_attrs_class(cls):
        import attr

        for a_field in attr.fields(cls):
            yield a_field.name, cast("type", a_field.type)

    elif is_pydantic_model(cls):
        for p_field in cls.__fields__.values():
            if p_field.field_info.allow_mutation:
                yield p_field.name, p_field.outer_type_

    elif is_msgspec_struct(cls):
        for m_field in cls.__struct_fields__:
            type_ = cls.__annotations__.get(m_field, None)
            yield m_field, type_


def _pick_equality_operator(type_: type) -> EqOperator:
    """Get the default equality operator for a given type."""
    np = sys.modules.get("numpy", None)
    if np is not None and hasattr(type_, "__array__"):
        return np.array_equal  # type: ignore [no-any-return]
    return operator.eq


@lru_cache(maxsize=None)
def _build_dataclass_signal_group(
    cls: type, equality_operators: Iterable[tuple[str, EqOperator]] | None = None
) -> type[SignalGroup]:
    """Build a SignalGroup with events for each field in a dataclass."""
    signals = {name: Signal(type_) for name, type_ in iter_fields(cls)}
    return type(f"{cls.__name__}SignalGroup", (SignalGroup,), signals)


def is_evented(obj: object) -> bool:
    """Return `True` if the object or its class has been decorated with evented."""
    return hasattr(obj, PSYGNAL_GROUP_NAME)


def get_evented_namespace(obj: object) -> str | None:
    """Return the name of the evented SignalGroup for an object.

    Note: if you get the returned name as an attribute of the object, it will be a
    SignalGroup instance only if `obj` is an *instance* of an evented class.
    If `obj` is the evented class itself, it will be a `_SignalGroupDescriptor`.

    Examples
    --------
    ```python
    from psygnal import evented, get_evented_namespace, is_evented

    @evented(events_namespace="my_events")
    class Foo:
        ...

    assert get_evented_namespace(Foo) == "my_events"
    assert is_evented(Foo)
    """
    return getattr(obj, PSYGNAL_GROUP_NAME, None)


def evented_setattr(
    owner: type[S], signal_group_name: str, field_names: Iterable[str] | None = None
) -> Callable[[S, str, Any], None]:
    """Create a new __setattr__ method that emits events when fields change.

    `signal_group_name` must point to an attribute on the `self` object provided to
    __setattr__ that obeys the following "SignalGroup interface":

        1. For every "evented" field in the class, there must be a corresponding
           attribute
        on the SignalGroup instance: `assert hasattr(signal_group, attr_name)` 2. The
        object returned by `getattr(signal_group, attr_name)` must be a
        SignalInstance-like object, i.e. it must have an `emit` method that accepts one
        (or more) positional arguments.

        ```python
        class SignalInstanceProtocol(Protocol):
            def emit(self, *args: Any) -> Any: ...

        class SignalGroupProtocol(Protocol):
            def __getattr__(self, name: str) -> SignalInstanceProtocol: ...
        ```

    Parameters
    ----------
    owner: type
        The class that will have a new __setattr__ method.
    signal_group_name : str, optional
        The name of the attribute on `self` that holds the `SignalGroup` instance, by
        default "_psygnal_group_".
    field_names : Iterable[str], optional
        The names of the fields that should be evented. If not provided, all mutable
        fields will be evented.
    """
    _fields = set(field_names) if field_names else set()

    def _setattr_and_emit_(self: Any, _attr_name: str, _value: Any) -> None:
        """New __setattr__ method that emits events when fields change."""
        if _attr_name not in _fields:
            super(owner, self).__setattr__(_attr_name, _value)
            return

        # get the signal group
        sig_group = getattr(self, signal_group_name, None)
        # if we don't have a signal instance for this attribute, just set it.
        if sig_group is None:  # pragma: no cover
            super(owner, self).__setattr__(_attr_name, _value)
            return

        # grab current value
        before = getattr(self, _attr_name, _NULL)

        # set value using original setter
        super(owner, self).__setattr__(_attr_name, _value)

        # check the new value and emit the event if different
        after = getattr(self, _attr_name)

        if (before is _NULL and after is not _NULL) or (
            not _get_eq_op(owner, _attr_name)(before, after)
        ):
            signal_instance = cast("SignalInstance", getattr(sig_group, _attr_name))
            signal_instance.emit(after)

    _setattr_and_emit_._fields_ = _fields  # type: ignore [attr-defined]
    return _setattr_and_emit_


class SignalGroupDescriptor:
    """Lazily create a SignalGroup when attribute is accessed.

    This descriptor is designed to be used as a class attribute on a dataclass-like
    class (e.g. a dataclass, a `pydantic.BaseModel`, an attrs class, a `msgspec.Struct`)
    On first access of the descriptor on an instance, it will create a `SignalGroup`
    with a signal for each field in the dataclass.

    Parameters
    ----------
    equality_operators : Dict[str, Callable[[Any, Any], bool]], optional
        A dictionary mapping field names to custom equality operators, where an equality
        operator is a callable that accepts two arguments and returns True if the two
        objects are equal. This will be used when comparing the old and new values of a
        field to determine whether to emit an event. If not provided, the default
        equality operator is `operator.eq`, except for numpy arrays, where
        `np.array_equal` is used.
    signal_group_class : Type[SignalGroup], optional
        A custom SignalGroup class to use, by default None
    warn_on_no_fields : bool, optional
        If `True` (the default), a warning will be emitted if no mutable dataclass-like
        fields are found on the object.
    cache_on_instance : bool, optional
        If `True` (the default), a newly-created SignalGroup instance will be cached on
        the instance itself, so that subsequent accesses to the descriptor will return
        the same SignalGroup instance.  This makes for slightly faster subsequent
        access, but means that the owner instance will no longer be pickleable.  If
        `False`, the SignalGroup instance will *still* be cached, but not on the
        instance itself.

    Examples
    --------
    ```python
    from typing import ClassVar
    from dataclasses import dataclass
    from psygnal import SignalGroupDescriptor

    @dataclass
    class Foo:
        bar: int
        baz: str
        events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor()

    foo = Foo(1, 'hi')
    foo.events.bar.connect(print)
    foo.bar = 2  # prints 2
    ```
    """

    def __init__(
        self,
        *,
        equality_operators: dict[str, EqOperator] | None = None,
        signal_group_class: type[SignalGroup] | None = None,
        warn_on_no_fields: bool = True,
        cache_on_instance: bool = True,
        field_names: Iterable[str] | None = None,
    ):
        self._signal_group = signal_group_class
        self._name: str | None = None
        self._eqop = tuple(equality_operators.items()) if equality_operators else None
        self._warn_on_no_fields = warn_on_no_fields
        self._cache_on_instance = cache_on_instance
        self._field_names = set(field_names) if field_names else set()

    def __set_name__(self, owner: type, name: str) -> None:
        """Called when this descriptor is added to class `owner` as attribute `name`."""
        self._name = name

        try:
            # assign a new __setattr__ method to the class
            owner.__setattr__ = evented_setattr(owner, name)  # type: ignore
        except Exception as e:  # pragma: no cover
            # not sure what might cause this ... but it will have consequences
            raise type(e)(
                f"Could not update __setattr__ on class: {owner}. Events will not be "
                "emitted when fields change."
            ) from e

        with contextlib.suppress(AttributeError):
            # This is the flag that identifies this object as evented
            setattr(owner, PSYGNAL_GROUP_NAME, name)

    # map of id(obj) -> SignalGroup
    # cached here in case the object isn't modifiable
    _instance_map: dict[int, SignalGroup] = {}

    @overload
    def __get__(self, instance: None, owner: type) -> SignalGroupDescriptor:
        ...

    @overload
    def __get__(self, instance: object, owner: type) -> SignalGroup:
        ...

    def __get__(
        self, instance: object, owner: type
    ) -> SignalGroup | SignalGroupDescriptor:
        """Return a SignalGroup instance for `instance`."""
        if instance is None:
            return self

        obj_id = id(instance)
        # if we haven't yet instantiated a SignalGroup for this instance,
        # do it now and cache it.  Note that we cache it here rather than
        # on the instance in case the instance is not modifiable.
        if obj_id not in self._instance_map:
            # now we definitely need a signal group class. So if we don't have one
            # yet, build it now.
            if self._signal_group is None:
                # (setting attr just for the sake of mypy)
                self._signal_group = self.build_signal_group(owner)

            group = self._signal_group(instance)
            # cache it
            self._instance_map[obj_id] = group
            # also *try* to set it on the instance as well, since it will skip all the
            # __get__ logic in the future, but if it fails, no big deal.
            if self._name and self._cache_on_instance:
                with contextlib.suppress(Exception):
                    setattr(instance, self._name, self._instance_map[obj_id])

            with contextlib.suppress(TypeError):
                # mypy says too many attributes for weakref.finalize, but it's wrong.
                weakref.finalize(  # type: ignore [call-arg]
                    instance, self._instance_map.pop, obj_id, None
                )

        return self._instance_map[obj_id]

    def build_signal_group(self, owner: type) -> type[SignalGroup]:
        """Build a SignalGroup for the given class and update this descriptor.

        Building of the SignalGroup is deferred until the first time it is accessed,
        so that we can be sure that the class has been fully initialized, and all
        dataclass-style fields have been added to the class. This method is provided
        as a way to manually trigger the build process.
        """
        self._signal_group = _build_dataclass_signal_group(owner, self._eqop)
        owner.__setattr__._fields_.update(self._signal_group._signals_)  # type: ignore
        if self._warn_on_no_fields and not self._signal_group._signals_:
            warnings.warn(
                f"No mutable fields found on class {owner}: no events will be "
                "emitted. (Is this a dataclass, attrs, msgspec, or pydantic model?)"
            )
        return self._signal_group
