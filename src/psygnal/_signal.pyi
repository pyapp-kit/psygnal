import threading
from inspect import Signature
from typing import (
    Any,
    Callable,
    ClassVar,
    ContextManager,
    Final,
    Generic,
    Iterable,
    Iterator,
    Literal,
    NewType,
    NoReturn,
    TypeVar,
    overload,
)

from _typeshed import Incomplete
from typing_extensions import TypeVarTuple, Unpack

from ._group import EmissionInfo
from ._weak_callback import RefErrorChoice, WeakCallback

__all__ = ["Signal", "SignalInstance", "_compiled", "ReemissionVal", "Unparametrized"]

ReducerOneArg = Callable[[Iterable[tuple]], tuple]
ReducerTwoArgs = Callable[[tuple, tuple], tuple]
ReducerFunc = ReducerOneArg | ReducerTwoArgs
_T1 = TypeVar("_T1")
_T2 = TypeVar("_T2")
_T3 = TypeVar("_T3")
_T4 = TypeVar("_T4")
_T5 = TypeVar("_T5")
RetT = TypeVar("RetT")
Ts = TypeVarTuple("Ts")
F = TypeVar("F", bound=Callable)
ReemissionVal = Literal["immediate", "queued", "latest-only"]
Unparametrized = NewType("Unparametrized", object)

class ReemissionMode:
    IMMEDIATE: Final[str]
    QUEUED: Final[str]
    LATEST: Final[str]
    @staticmethod
    def validate(value: str) -> str: ...
    @staticmethod
    def _members() -> set[str]: ...

class Signal(Generic[Unpack[Ts]]):
    _current_emitter: ClassVar[SignalInstance | None]
    _name: Incomplete
    description: Incomplete
    _check_nargs_on_connect: Incomplete
    _check_types_on_connect: Incomplete
    _reemission: Incomplete
    _signal_instance_class: Incomplete
    _signal_instance_cache: Incomplete
    _types: Incomplete
    def __init__(
        self,
        *types: Unpack[Ts],
        description: str = "",
        name: str | None = None,
        check_nargs_on_connect: bool = True,
        check_types_on_connect: bool = False,
        reemission: ReemissionVal = ...,
    ) -> None: ...
    @property
    def signature(self) -> Signature: ...
    def __set_name__(self, owner: type[Any], name: str) -> None: ...
    @overload
    def __get__(
        self, instance: None, owner: type[Any] | None = None
    ) -> Signal[Unpack[Ts]]: ...
    @overload
    def __get__(
        self, instance: Any, owner: type[Any] | None = None
    ) -> SignalInstance[Unpack[Ts]]: ...
    def _cache_signal_instance(
        self, instance: Any, signal_instance: SignalInstance
    ) -> None: ...
    def _create_signal_instance(
        self, instance: Any, name: str | None = None
    ) -> SignalInstance[Unpack[Ts]]: ...
    @classmethod
    def _emitting(cls, emitter: SignalInstance) -> Iterator[None]: ...
    @classmethod
    def current_emitter(cls) -> SignalInstance | None: ...
    @classmethod
    def sender(cls) -> Any: ...

class SignalInstance(Generic[Unpack[Ts]]):
    _is_blocked: bool
    _is_paused: bool
    _debug_hook: ClassVar[Callable[[EmissionInfo], None] | None]
    _reemission: Incomplete
    _name: Incomplete
    _instance: Incomplete
    _args_queue: Incomplete
    _types: Incomplete
    _check_nargs_on_connect: Incomplete
    _check_types_on_connect: Incomplete
    _slots: Incomplete
    _lock: Incomplete
    _emit_queue: Incomplete
    _recursion_depth: int
    _max_recursion_depth: int
    _run_emit_loop_inner: Incomplete
    _priority_in_use: bool
    def __init__(
        self,
        types: tuple[Unpack[Ts]] | Signature = (),
        instance: Any = None,
        name: str | None = None,
        check_nargs_on_connect: bool = True,
        check_types_on_connect: bool = False,
        reemission: ReemissionVal = ...,
    ) -> None: ...
    @staticmethod
    def _instance_ref(instance: Any) -> Callable[[], Any]: ...
    @property
    def signature(self) -> Signature: ...
    @property
    def instance(self) -> Any: ...
    @property
    def name(self) -> str: ...
    def __repr__(self) -> str: ...
    @overload
    @overload
    def connect(
        self: SignalInstance[()],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2]],
        slot: Callable[[_T1, _T2], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3]],
        slot: Callable[[_T1, _T2], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3]],
        slot: Callable[[_T1, _T2, _T3], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[_T1, _T2], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[_T1, _T2, _T3], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[_T1, _T2, _T3, _T4], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3, _T4], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1, _T2], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1, _T2, _T3], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1, _T2, _T3, _T4], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3, _T4], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1, _T2, _T3, _T4, _T5], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3, _T4, _T5], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[Unparametrized],
        slot: F,
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> F: ...
    @overload
    def connect(
        self: SignalInstance,
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[F], F]: ...
    @overload
    @overload
    def connect(
        self: SignalInstance[()],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2]],
        slot: Callable[[_T1, _T2], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3]],
        slot: Callable[[_T1, _T2], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3]],
        slot: Callable[[_T1, _T2, _T3], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[_T1, _T2], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[_T1, _T2, _T3], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[_T1, _T2, _T3, _T4], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3, _T4], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1, _T2], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1, _T2, _T3], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1, _T2, _T3, _T4], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3, _T4], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1, _T2, _T3, _T4, _T5], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3, _T4, _T5], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[Unparametrized],
        slot: F,
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> F: ...
    @overload
    def connect(
        self: SignalInstance,
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[F], F]: ...
    def _append_slot(self, slot: WeakCallback) -> None: ...
    def _remove_slot(self, slot: Literal["all"] | int | WeakCallback) -> None: ...
    def _try_discard(self, callback: WeakCallback, missing_ok: bool = True) -> None: ...
    @overload
    def connect(
        self: SignalInstance[()],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2]],
        slot: Callable[[_T1, _T2], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3]],
        slot: Callable[[_T1, _T2], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3]],
        slot: Callable[[_T1, _T2, _T3], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[_T1, _T2], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[_T1, _T2, _T3], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[_T1, _T2, _T3, _T4], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3, _T4], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1, _T2], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1, _T2, _T3], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1, _T2, _T3, _T4], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3, _T4], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1, _T2, _T3, _T4, _T5], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3, _T4, _T5], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[Unparametrized],
        slot: F,
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> F: ...
    @overload
    def connect(
        self: SignalInstance,
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[F], F]: ...
    def disconnect_setattr(
        self, obj: object, attr: str, missing_ok: bool = True
    ) -> None: ...
    @overload
    def connect(
        self: SignalInstance[()],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2]],
        slot: Callable[[_T1, _T2], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3]],
        slot: Callable[[_T1, _T2], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3]],
        slot: Callable[[_T1, _T2, _T3], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[_T1, _T2], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[_T1, _T2, _T3], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4]],
        slot: Callable[[_T1, _T2, _T3, _T4], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3, _T4], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1, _T2], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1, _T2, _T3], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1, _T2, _T3, _T4], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3, _T4], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[type[_T1], type[_T2], type[_T3], type[_T4], type[_T5]],
        slot: Callable[[_T1, _T2, _T3, _T4, _T5], RetT],
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[_T1, _T2, _T3, _T4, _T5], RetT]: ...
    @overload
    def connect(
        self: SignalInstance[Unparametrized],
        slot: F,
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> F: ...
    @overload
    def connect(
        self: SignalInstance,
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
    ) -> Callable[[F], F]: ...
    def disconnect_setitem(
        self, obj: object, key: str, missing_ok: bool = True
    ) -> None: ...
    def _check_nargs(
        self, slot: Callable, spec: Signature
    ) -> tuple[Signature | None, int | None, bool]: ...
    def _raise_connection_error(self, slot: Callable, extra: str = "") -> NoReturn: ...
    def _slot_index(self, slot: Callable) -> int: ...
    def disconnect(
        self, slot: Callable | None = None, missing_ok: bool = True
    ) -> None: ...
    def __contains__(self, slot: Callable) -> bool: ...
    def __len__(self) -> int: ...
    def emit(
        self, *args: Any, check_nargs: bool = False, check_types: bool = False
    ) -> None: ...
    def __call__(
        self, *args: Any, check_nargs: bool = False, check_types: bool = False
    ) -> None: ...
    def _run_emit_loop(self, args: tuple[Any, ...]) -> None: ...
    def _run_emit_loop_immediate(self) -> None: ...
    _args: Incomplete
    _caller: Incomplete
    def _run_emit_loop_latest_only(self) -> None: ...
    def _run_emit_loop_queued(self) -> None: ...
    def block(self, exclude: Iterable[str | SignalInstance] = ()) -> None: ...
    def unblock(self) -> None: ...
    def blocked(self) -> ContextManager[None]: ...
    def pause(self) -> None: ...
    def resume(
        self, reducer: ReducerFunc | None = None, initial: Any = ...
    ) -> None: ...
    def paused(
        self, reducer: ReducerFunc | None = None, initial: Any = ...
    ) -> ContextManager[None]: ...
    def __getstate__(self) -> dict: ...
    def __setstate__(self, state: dict) -> None: ...

class _SignalBlocker:
    _signal: Incomplete
    _exclude: Incomplete
    _was_blocked: Incomplete
    def __init__(
        self, signal: SignalInstance, exclude: Iterable[str | SignalInstance] = ()
    ) -> None: ...
    def __enter__(self) -> None: ...
    def __exit__(self, *args: Any) -> None: ...

class _SignalPauser:
    _was_paused: Incomplete
    _signal: Incomplete
    _reducer: Incomplete
    _initial: Incomplete
    def __init__(
        self, signal: SignalInstance, reducer: ReducerFunc | None, initial: Any
    ) -> None: ...
    def __enter__(self) -> None: ...
    def __exit__(self, *args: Any) -> None: ...

_compiled: bool
