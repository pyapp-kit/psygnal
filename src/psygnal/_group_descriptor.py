from __future__ import annotations

import contextlib
import copy
import operator
import sys
import warnings
import weakref
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Literal,
    Optional,
    TypeVar,
    cast,
    overload,
)

from ._dataclass_utils import iter_fields
from ._group import SignalGroup
from ._signal import Signal, SignalInstance

if TYPE_CHECKING:
    from _weakref import ref as ref
    from collections.abc import Iterable, Mapping

    from typing_extensions import TypeAlias

    from psygnal._weak_callback import RefErrorChoice, WeakCallback

    EqOperator: TypeAlias = Callable[[Any, Any], bool]
    FieldAliasFunc: TypeAlias = Callable[[str], Optional[str]]

__all__ = ["SignalGroupDescriptor", "get_evented_namespace", "is_evented"]


T = TypeVar("T", bound=type)
S = TypeVar("S")


_EQ_OPERATORS: dict[type, dict[str, EqOperator]] = {}
_EQ_OPERATOR_NAME = "__eq_operators__"
PSYGNAL_GROUP_NAME = "_psygnal_group_"
PATCHED_BY_PSYGNAL = "_patched_by_psygnal_"
_NULL = object()


def _get_eq_operator_map(cls: type) -> dict[str, EqOperator]:
    """Return the map of field_name -> equality operator for the class."""
    # if the class has an __eq_operators__ attribute, we use it
    # otherwise use/create the entry for `cls` in the global _EQ_OPERATORS map
    if hasattr(cls, _EQ_OPERATOR_NAME):
        return cast("dict", getattr(cls, _EQ_OPERATOR_NAME))
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
        # field didn't exist to begin with (unlikely)
        return after is _NULL  # pragma: no cover

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
        else:  # pragma: no cover
            # at some point, dask array started hitting in the above condition
            # so we add explicit casing in _pick_equality_operator
            # but we keep this fallback just in case
            eq_map[name] = operator.is_
            return _check_field_equality(cls, name, before, after, _fail=True)


def _pick_equality_operator(type_: type | None) -> EqOperator:
    """Get the default equality operator for a given type."""
    np = sys.modules.get("numpy", None)
    if getattr(type_, "__module__", "").startswith("dask"):
        # for dask, simply check if the values are the same object
        # this is to avoid accidentally triggering a computation with array_equal
        return operator.is_
    if np is not None and hasattr(type_, "__array__"):
        return np.array_equal  # type: ignore [no-any-return]
    return operator.eq


class _DataclassFieldSignalInstance(SignalInstance):
    def connect_setattr(
        self,
        obj: ref | object,
        attr: str,
        maxargs: int | None | object = 1,
        *,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> WeakCallback[None]:
        return super().connect_setattr(
            obj, attr, maxargs, on_ref_error=on_ref_error, priority=priority
        )


def _build_dataclass_signal_group(
    cls: type,
    signal_group_class: type[SignalGroup],
    equality_operators: Iterable[tuple[str, EqOperator]] | None = None,
    signal_aliases: Mapping[str, str | None] | FieldAliasFunc | None = None,
) -> type[SignalGroup]:
    """Build a SignalGroup with events for each field in a dataclass.

    Parameters
    ----------
    cls : type
        the dataclass to look for the fields to connect with signals.
    signal_group_class: type[SignalGroup]
        SignalGroup or a subclass of it, to use as a super class.
        Default to SignalGroup
    equality_operators: Iterable[tuple[str, EqOperator]] | None
        If defined, a mapping of field name and equality operator to use to compare if
        each field was modified after being set.
        Default to None
    signal_aliases: Mapping[str, str | None] | Callable[[str], str | None] | None
        If defined, a mapping between field name and signal name. Field names that are
        not `signal_aliases` keys are not aliased (the signal name is the field name).
        If the dict value is None, do not create a signal associated with this field.
        If a callable, the signal name is the output of the function applied to the
        field name. If the output is None, no signal is created for this field.
        If None, defaults to an empty dict, no aliases.
        Default to None

    """
    group_name = f"{cls.__name__}{signal_group_class.__name__}"
    # parse arguments
    _equality_operators = dict(equality_operators) if equality_operators else {}
    eq_map = _get_eq_operator_map(cls)

    # prepare signal_aliases lookup
    transform: FieldAliasFunc | None = None
    _signal_aliases: dict[str, str | None] = {}
    if callable(signal_aliases):
        transform = signal_aliases
    else:
        _signal_aliases = dict(signal_aliases) if signal_aliases else {}
    signal_group_sig_names = list(getattr(signal_group_class, "_psygnal_signals", {}))
    signal_group_sig_aliases = cast(
        "dict[str, str | None]",
        dict(getattr(signal_group_class, "_psygnal_aliases", {})),
    )

    signals = {}
    # create a Signal for each field in the dataclass
    for name, type_ in iter_fields(cls):
        if name in _equality_operators:
            if not callable(_equality_operators[name]):  # pragma: no cover
                raise TypeError("EqOperator must be callable")
            eq_map[name] = _equality_operators[name]
        else:
            eq_map[name] = _pick_equality_operator(type_)

        # Resolve the signal name for the field
        sig_name: str | None
        if name in _signal_aliases:  # an alias has been provided in a mapping
            sig_name = _signal_aliases[name]
        elif callable(transform):  # a callable has been provided
            _signal_aliases[name] = sig_name = transform(name)
        elif name in signal_group_sig_aliases:  # an alias has been defined in the class
            _signal_aliases[name] = sig_name = signal_group_sig_aliases[name]
        else:  # no alias has been defined, use the field name as the signal name
            sig_name = name

        # An alias mapping or callable returned `None`, skip this field
        if sig_name is None:
            continue

        # Repeated signal
        if sig_name in signals:
            key = next((k for k, v in _signal_aliases.items() if v == sig_name), None)
            warnings.warn(
                f"Skip signal {sig_name!r}, was already created in {group_name}, "
                f"from field {key}",
                UserWarning,
                stacklevel=2,
            )
            continue
        if sig_name in signal_group_sig_names:
            warnings.warn(
                f"Skip signal {sig_name!r}, was already defined by "
                f"{signal_group_class}",
                UserWarning,
                stacklevel=2,
            )
            continue

        # Create the Signal
        field_type = object if type_ is None else type_
        signals[sig_name] = sig = Signal(field_type, field_type)
        # patch in our custom SignalInstance class with maxargs=1 on connect_setattr
        sig._signal_instance_class = _DataclassFieldSignalInstance

    # Create `signal_group_class` subclass with the attached signals and signal_aliases
    return type(
        group_name, (signal_group_class,), signals, signal_aliases=_signal_aliases
    )


def is_evented(obj: object) -> bool:
    """Return `True` if the object or its class has been decorated with evented.

    This also works for a __setattr__ method that has been patched by psygnal.
    """
    return hasattr(obj, PSYGNAL_GROUP_NAME) or hasattr(obj, PATCHED_BY_PSYGNAL)


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
    class Foo: ...


    assert get_evented_namespace(Foo) == "my_events"
    assert is_evented(Foo)
    ```
    """
    return getattr(obj, PSYGNAL_GROUP_NAME, None)


def get_signal_from_field(group: SignalGroup, name: str) -> SignalInstance | None:
    """Get the signal from a SignalGroup corresponding to the field `name`.

    Parameters
    ----------
    group: SignalGroup
        the signal group attached to a dataclass.
    name: str
        the name of field

    Returns
    -------
    SignalInstance | None
        the `SignalInstance` corresponding with the field `name` or None if the field
        was skipped or does not have an associated `SignalInstance`.
    """
    sig_name = group._psygnal_aliases.get(name, name)
    if sig_name is None or sig_name not in group:
        return None
    return group[sig_name]


class _changes_emitted:
    def __init__(self, obj: object, field: str, signal: SignalInstance) -> None:
        self.obj = obj
        self.field = field
        self.signal = signal

    def __enter__(self) -> None:
        self._prev = getattr(self.obj, self.field, _NULL)

    def __exit__(self, *args: Any) -> None:
        new: Any = getattr(self.obj, self.field, _NULL)
        if not _check_field_equality(type(self.obj), self.field, self._prev, new):
            self.signal.emit(new, self._prev)


SetAttr = Callable[[Any, str, Any], None]


@overload
def evented_setattr(
    signal_group_name: str, super_setattr: SetAttr, with_aliases: bool = ...
) -> SetAttr: ...


@overload
def evented_setattr(
    signal_group_name: str,
    super_setattr: Literal[None] | None = ...,
    with_aliases: bool = ...,
) -> Callable[[SetAttr], SetAttr]: ...


def evented_setattr(
    signal_group_name: str,
    super_setattr: SetAttr | None = None,
    with_aliases: bool = True,
) -> SetAttr | Callable[[SetAttr], SetAttr]:
    """Create a new __setattr__ method that emits events when fields change.

    `signal_group_name` MUST point to an attribute on the `self` object provided to
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
    signal_group_name : str, optional
        The name of the attribute on `self` that holds the `SignalGroup` instance, by
        default "_psygnal_group_".
    super_setattr: Callable
        The original __setattr__ method for the class.
    with_aliases: bool, optional
        Whether to lookup the signal name in the signal aliases mapping,
        by default True.  This is slightly slower, and so can be set to False if you
        know you don't have any signal aliases.
    """

    def _inner(super_setattr: SetAttr) -> SetAttr:
        # don't patch twice
        if getattr(super_setattr, PATCHED_BY_PSYGNAL, False):
            return super_setattr

        # pick a slightly faster signal lookup if we don't need aliases
        get_signal: Callable[[SignalGroup, str], SignalInstance | None] = (
            get_signal_from_field if with_aliases else SignalGroup.__getitem__
        )

        def _setattr_and_emit_(self: object, name: str, value: Any) -> None:
            """New __setattr__ method that emits events when fields change."""
            if name == signal_group_name:
                return super_setattr(self, name, value)

            group = cast("SignalGroup", getattr(self, signal_group_name))
            if not with_aliases and name not in group:
                return super_setattr(self, name, value)

            # don't emit if the signal doesn't exist or has no listeners
            signal: SignalInstance | None = get_signal(group, name)
            if signal is None or len(signal) < 1:
                return super_setattr(self, name, value)

            with _changes_emitted(self, name, signal):
                super_setattr(self, name, value)

        setattr(_setattr_and_emit_, PATCHED_BY_PSYGNAL, True)
        return _setattr_and_emit_

    return _inner(super_setattr) if super_setattr else _inner


class SignalGroupDescriptor:
    """Create a [`psygnal.SignalGroup`][] on first instance attribute access.

    This descriptor is designed to be used as a class attribute on a dataclass-like
    class (e.g. a [`dataclass`](https://docs.python.org/3/library/dataclasses.html), a
    [`pydantic.BaseModel`](https://docs.pydantic.dev/usage/models/), an
    [attrs](https://www.attrs.org/en/stable/overview.html) class, a
    [`msgspec.Struct`](https://jcristharif.com/msgspec/structs.html)) On first access of
    the descriptor on an instance, it will create a [`SignalGroup`][psygnal.SignalGroup]
    bound to the instance, with a [`SignalInstance`][psygnal.SignalInstance] for each
    field in the dataclass.

    !!!important
        Using this descriptor will *patch* the class's `__setattr__` method to emit
        events when fields change. (That patching occurs on first access of the
        descriptor name on an instance).  To prevent this patching, you can set
        `patch_setattr=False` when creating the descriptor, but then you will need to
        manually call `emit` on the appropriate `SignalInstance` when you want to emit
        an event.  Or you can use `evented_setattr` yourself

        ```python
        from psygnal._group_descriptor import evented_setattr
        from psygnal import SignalGroupDescriptor
        from dataclasses import dataclass
        from typing import ClassVar


        @dataclass
        class Foo:
            x: int
            _events: ClassVar = SignalGroupDescriptor(patch_setattr=False)

            @evented_setattr("_events")  # pass the name of your SignalGroup
            def __setattr__(self, name: str, value: Any) -> None:
                super().__setattr__(name, value)
        ```

        *This currently requires a private import, please open an issue if you would
        like to depend on this functionality.*

    Parameters
    ----------
    equality_operators : dict[str, Callable[[Any, Any], bool]], optional
        A dictionary mapping field names to custom equality operators, where an equality
        operator is a callable that accepts two arguments and returns True if the two
        objects are equal. This will be used when comparing the old and new values of a
        field to determine whether to emit an event. If not provided, the default
        equality operator is `operator.eq`, except for numpy arrays, where
        `np.array_equal` is used.
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
    patch_setattr : bool, optional
        If `True` (the default), a new `__setattr__` method will be created that emits
        events when fields change.  If `False`, no `__setattr__` method will be
        created.  (This will prevent signal emission, and assumes you are using a
        different mechanism to emit signals when fields change.)
    signal_group_class : type[SignalGroup] | None, optional
        A custom SignalGroup class to use, SignalGroup if None, by default None
    collect_fields : bool, optional
        Create a signal for each field in the dataclass. If True, the `SignalGroup`
        instance will be a subclass of `signal_group_class` (SignalGroup if it is None).
        If False, a deepcopy of `signal_group_class` will be used.
        Default to True
    signal_aliases: Mapping[str, str | None] | Callable[[str], str | None] | None
        If defined, a mapping between field name and signal name. Field names that are
        not `signal_aliases` keys are not aliased (the signal name is the field name).
        If the dict value is None, do not create a signal associated with this field.
        If a callable, the signal name is the output of the function applied to the
        field name. If the output is None, no signal is created for this field.
        If None, defaults to an empty dict, no aliases.
        Default to None

    Examples
    --------
    ```python
    from typing import ClassVar
    from dataclasses import dataclass
    from psygnal import SignalGroupDescriptor


    @dataclass
    class Person:
        name: str
        age: int = 0
        events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor()


    john = Person("John", 40)
    john.events.age.connect(print)
    john.age += 1  # prints 41
    ```
    """

    # map of id(obj) -> SignalGroup
    # cached here in case the object isn't modifiable
    _instance_map: ClassVar[dict[int, SignalGroup]] = {}

    def __init__(
        self,
        *,
        equality_operators: dict[str, EqOperator] | None = None,
        warn_on_no_fields: bool = True,
        cache_on_instance: bool = True,
        patch_setattr: bool = True,
        signal_group_class: type[SignalGroup] | None = None,
        collect_fields: bool = True,
        signal_aliases: Mapping[str, str | None] | FieldAliasFunc | None = None,
    ):
        grp_cls = signal_group_class or SignalGroup
        if not (isinstance(grp_cls, type) and issubclass(grp_cls, SignalGroup)):
            raise TypeError(  # pragma: no cover
                f"'signal_group_class' must be a subclass of SignalGroup, not {grp_cls}"
            )
        if not collect_fields:
            if grp_cls is SignalGroup:
                raise ValueError(
                    "Cannot use SignalGroup with `collect_fields=False`. "
                    "Use a custom SignalGroup subclass instead."
                )

            if callable(signal_aliases):
                raise ValueError(
                    "Cannot use a Callable for `signal_aliases` with "
                    "`collect_fields=False`"
                )

        self._name: str | None = None
        self._eqop = tuple(equality_operators.items()) if equality_operators else None
        self._warn_on_no_fields = warn_on_no_fields
        self._cache_on_instance = cache_on_instance
        self._patch_setattr = patch_setattr
        self._signal_group_class: type[SignalGroup] = grp_cls
        self._collect_fields = collect_fields
        self._signal_aliases = signal_aliases

        self._signal_groups: dict[int, type[SignalGroup]] = {}

    def __set_name__(self, owner: type, name: str) -> None:
        """Called when this descriptor is added to class `owner` as attribute `name`."""
        self._name = name
        with contextlib.suppress(AttributeError):
            # This is the flag that identifies this object as evented
            setattr(owner, PSYGNAL_GROUP_NAME, name)

    def _do_patch_setattr(self, owner: type, with_aliases: bool = True) -> None:
        """Patch the owner class's __setattr__ method to emit events."""
        if not self._patch_setattr:
            return
        if getattr(owner.__setattr__, PATCHED_BY_PSYGNAL, False):
            return

        name = self._name
        if not (name and hasattr(owner, name)):  # pragma: no cover
            # this should never happen... but if it does, we'll get errors
            # every time we set an attribute on the class.  So raise now.
            raise AttributeError("SignalGroupDescriptor has not been set on the class")

        try:
            # assign a new __setattr__ method to the class
            owner.__setattr__ = evented_setattr(  # type: ignore
                name,
                owner.__setattr__,  # type: ignore
                with_aliases=with_aliases,
            )
        except Exception as e:  # pragma: no cover
            # not sure what might cause this ... but it will have consequences
            raise type(e)(
                f"Could not update __setattr__ on class: {owner}. Events will not be "
                "emitted when fields change."
            ) from e

    @overload
    def __get__(self, instance: None, owner: type) -> SignalGroupDescriptor: ...

    @overload
    def __get__(self, instance: object, owner: type) -> SignalGroup: ...

    def __get__(
        self, instance: object, owner: type
    ) -> SignalGroup | SignalGroupDescriptor:
        """Return a SignalGroup instance for `instance`."""
        if instance is None:
            return self

        signal_group = self._get_signal_group(owner)

        # if we haven't yet instantiated a SignalGroup for this instance,
        # do it now and cache it.  Note that we cache it here in addition to
        # the instance (in case the instance is not modifiable).
        obj_id = id(instance)
        if obj_id not in self._instance_map:
            # cache it
            self._instance_map[obj_id] = signal_group(instance)
            # also *try* to set it on the instance as well, since it will skip all the
            # __get__ logic in the future, but if it fails, no big deal.
            if self._name and self._cache_on_instance:
                with contextlib.suppress(Exception):
                    setattr(instance, self._name, self._instance_map[obj_id])

            # clean up the cache when the instance is deleted
            with contextlib.suppress(TypeError):  # if it's not weakref-able
                weakref.finalize(instance, self._instance_map.pop, obj_id, None)

        return self._instance_map[obj_id]

    def _get_signal_group(self, owner: type) -> type[SignalGroup]:
        type_id = id(owner)
        if type_id not in self._signal_groups:
            self._signal_groups[type_id] = self._create_group(owner)
        return self._signal_groups[type_id]

    def _create_group(self, owner: type) -> type[SignalGroup]:
        if not self._collect_fields:
            # Do not collect fields from owner class
            Group = copy.deepcopy(self._signal_group_class)

            # Add aliases
            if isinstance(self._signal_aliases, dict):
                Group._psygnal_aliases.update(self._signal_aliases)

        else:
            # Collect fields and create SignalGroup subclass
            Group = _build_dataclass_signal_group(
                owner,
                self._signal_group_class,
                equality_operators=self._eqop,
                signal_aliases=self._signal_aliases,
            )

        if self._warn_on_no_fields and not Group._psygnal_signals:
            warnings.warn(
                f"No mutable fields found on class {owner}: no events will be "
                "emitted. (Is this a dataclass, attrs, msgspec, or pydantic model?)",
                stacklevel=2,
            )

        self._do_patch_setattr(owner, with_aliases=bool(Group._psygnal_aliases))
        return Group
