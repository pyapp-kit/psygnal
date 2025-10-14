from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypeVar, overload

from psygnal._group_descriptor import SignalGroupDescriptor

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from psygnal._group_descriptor import EqOperator, FieldAliasFunc

__all__ = ["evented"]

T = TypeVar("T", bound=type)


@overload
def evented(
    cls: T,
    *,
    events_namespace: str = "events",
    equality_operators: dict[str, EqOperator] | None = None,
    warn_on_no_fields: bool = ...,
    cache_on_instance: bool = ...,
    connect_child_events: bool = ...,
    signal_aliases: Mapping[str, str | None] | FieldAliasFunc | None = ...,
) -> T: ...
@overload
def evented(
    cls: Literal[None] | None = None,
    *,
    events_namespace: str = "events",
    equality_operators: dict[str, EqOperator] | None = None,
    warn_on_no_fields: bool = ...,
    cache_on_instance: bool = ...,
    connect_child_events: bool = ...,
    signal_aliases: Mapping[str, str | None] | FieldAliasFunc | None = ...,
) -> Callable[[T], T]: ...
def evented(
    cls: T | None = None,
    *,
    events_namespace: str = "events",
    equality_operators: dict[str, EqOperator] | None = None,
    warn_on_no_fields: bool = True,
    cache_on_instance: bool = True,
    connect_child_events: bool = True,
    signal_aliases: Mapping[str, str | None] | FieldAliasFunc | None = None,
) -> Callable[[T], T] | T:
    """A decorator to add events to a dataclass.

    See also the documentation for
    [`SignalGroupDescriptor`][psygnal.SignalGroupDescriptor].  This decorator is
    equivalent setting a class variable named `events` to a new
    `SignalGroupDescriptor` instance.

    Note that this decorator will modify `cls` *in place*, as well as return it.

    !!!tip
        It is recommended to use the `SignalGroupDescriptor` descriptor rather than
        the decorator, as it it is more explicit and provides for easier static type
        inference.

    Parameters
    ----------
    cls : type
        The class to decorate.
    events_namespace : str
        The name of the namespace to add the events to, by default `"events"`
    equality_operators : dict[str, Callable] | None
        A dictionary mapping field names to equality operators (a function that takes
        two values and returns `True` if they are equal). These will be used to
        determine if a field has changed when setting a new value.  By default, this
        will use the `__eq__` method of the field type, or np.array_equal, for numpy
        arrays.  But you can provide your own if you want to customize how equality is
        checked. Alternatively, if the class has an `__eq_operators__` class attribute,
        it will be used.
    warn_on_no_fields : bool
        If `True` (the default), a warning will be emitted if no mutable dataclass-like
        fields are found on the object.
    cache_on_instance : bool, optional
        If `True` (the default), a newly-created SignalGroup instance will be cached on
        the instance itself, so that subsequent accesses to the descriptor will return
        the same SignalGroup instance.  This makes for slightly faster subsequent
        access, but means that the owner instance will no longer be pickleable.  If
        `False`, the SignalGroup instance will *still* be cached, but not on the
        instance itself.
    connect_child_events : bool, optional
        If `True`, will connect events from all fields on the dataclass whose type is
        also "evented" (as determined by the `psygnal.is_evented` function,
        which returns True if the class has been decorated with `@evented`, or if it
        has a SignalGroupDescriptor) to the group on the parent object. By default
        True.
        This is useful for nested evented dataclasses, where you want to monitor events
        emitted from arbitrarily deep children on the parent object.
    signal_aliases: Mapping[str, str | None] | Callable[[str], str | None] | None
        If defined, a mapping between field name and signal name. Field names that are
        not `signal_aliases` keys are not aliased (the signal name is the field name).
        If the dict value is None, do not create a signal associated with this field.
        If a callable, the signal name is the output of the function applied to the
        field name. If the output is None, no signal is created for this field.
        If None, defaults to an empty dict, no aliases.
        Default to None

    Returns
    -------
    type
        The decorated class, which gains a new SignalGroup instance at the
        `events_namespace` attribute (by default, `events`).

    Raises
    ------
    TypeError
        If the class is frozen or is not a class.

    Examples
    --------
    ```python
    from psygnal import evented
    from dataclasses import dataclass


    @evented
    @dataclass
    class Person:
        name: str
        age: int = 0
    ```
    """

    def _decorate(cls: T) -> T:
        if not isinstance(cls, type):  # pragma: no cover
            raise TypeError("evented can only be used on classes")
        if any(k.startswith("_psygnal") for k in getattr(cls, "__annotations__", {})):
            raise TypeError("Fields on an evented class cannot start with '_psygnal'")

        descriptor: SignalGroupDescriptor = SignalGroupDescriptor(
            equality_operators=equality_operators,
            warn_on_no_fields=warn_on_no_fields,
            cache_on_instance=cache_on_instance,
            connect_child_events=connect_child_events,
            signal_aliases=signal_aliases,
        )
        # as a decorator, this will have already been called
        descriptor.__set_name__(cls, events_namespace)
        setattr(cls, events_namespace, descriptor)
        return cls

    return _decorate(cls) if cls is not None else _decorate
