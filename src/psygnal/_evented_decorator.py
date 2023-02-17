from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Optional,
    Type,
    TypeVar,
    Union,
    overload,
)

from ._group_descriptor import SignalGroupDescriptor

if TYPE_CHECKING:
    from typing_extensions import Literal

__all__ = ["evented"]

T = TypeVar("T", bound=Type)

EqOperator = Callable[[Any, Any], bool]
PSYGNAL_GROUP_NAME = "_psygnal_group_"
_NULL = object()


@overload
def evented(
    cls: T,
    *,
    events_namespace: str = "events",
    equality_operators: Optional[Dict[str, EqOperator]] = None,
) -> T:
    ...


@overload
def evented(
    cls: "Literal[None]" = None,
    *,
    events_namespace: str = "events",
    equality_operators: Optional[Dict[str, EqOperator]] = None,
) -> Callable[[T], T]:
    ...


def evented(
    cls: Optional[T] = None,
    *,
    events_namespace: str = "events",
    equality_operators: Optional[Dict[str, EqOperator]] = None,
) -> Union[Callable[[T], T], T]:
    """A decorator to add events to a dataclass.

    Supports [dataclass][dataclasses.dataclass], [attrs](https://www.attrs.org),
    [msgspec](https://jcristharif.com/msgspec/) and
    [pydantic](https://pydantic-docs.helpmanual.io) models.

    Note that this decorator will modify `cls` *in place*, as well as return it.

    Parameters
    ----------
    cls : type
        The class to decorate.
    events_namespace : str
        The name of the namespace to add the events to, by default `"events"`
    equality_operators : Optional[Dict[str, Callable]]
        A dictionary mapping field names to equality operators (a function that takes
        two values and returns `True` if they are equal). These will be used to
        determine if a field has changed when setting a new value.  By default, this
        will use the `__eq__` method of the field type, or np.array_equal, for numpy
        arrays.  But you can provide your own if you want to customize how equality is
        checked. Alternatively, if the class has an `__eq_operators__` class attribute,
        it will be used.

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

        descriptor = SignalGroupDescriptor(
            name=events_namespace, equality_operators=equality_operators
        )
        # as a decorator, this will have already been called
        descriptor.__set_name__(cls, events_namespace)
        setattr(cls, events_namespace, descriptor)
        return cls

    return _decorate(cls) if cls is not None else _decorate
