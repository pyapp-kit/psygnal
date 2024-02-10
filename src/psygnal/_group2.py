from typing import Any, Mapping, NamedTuple

from psygnal._signal import Signal, SignalInstance


class SignalAggInstance(SignalInstance):
    def _slot_relay(self, *args: Any) -> None:
        emitter = Signal.current_emitter()
        if emitter:
            info = EmissionInfo(emitter, args)
            self._run_emit_loop((info,))


class EmissionInfo(NamedTuple):
    """Tuple containing information about an emission event.

    Attributes
    ----------
    signal : SignalInstance
    args: tuple
    """

    signal: SignalInstance
    args: tuple[Any, ...]


class SignalGroup:
    _signals_: Mapping[str, Signal]

    def __init__(self, instance: Any = None) -> None:
        self._instance = instance
        self._signal_instances = {n: getattr(self, n) for n in type(self)._signals_}

    def __init_subclass__(cls, strict: bool = False) -> None:
        """Finds all Signal instances on the class and add them to `cls._signals_`."""
        cls._signals_ = {}
        for k in dir(cls):
            v = getattr(cls, k)
            if isinstance(v, Signal):
                cls._signals_[k] = v
        super().__init_subclass__()

    def __getitem__(self, item: str) -> Signal:
        return self._signals_[item]

    def __getattr__(self, name: str) -> Signal:
        if name in self._signals_:
            return self._signals_[name]
        if name == "signals":  # for backwards compatibility
            # TODO: add deprecation warning
            return self._signal_instances  # type: ignore
        raise AttributeError(f"{type(self).__name__!r} has no attribute {name!r}")

    def __len__(self) -> int:
        return len(self._signals_)

    def connect(self, *args, **kwargs) -> None:
        breakpoint()


class MyGroup(SignalGroup):
    sig1 = Signal(int)
    sig2 = Signal(str)


g = MyGroup()
