# type: ignore
from functools import partial

from psygnal import Signal, SignalInstance


class CreateSuite:
    def time_create_signal(self):
        _ = Signal()

    def time_create_signal_instance(self):
        _ = SignalInstance()


class E:
    changed = Signal(int)


class R:
    x: int = 0

    def method(self, x: int):
        list(range(2))  # simulate a brief thing

    def method2(self, x: int, y: int):
        list(range(2))  # simulate a brief thing

    @property
    def attr(self) -> int:
        return self.x

    @attr.setter
    def attr(self, value: int) -> None:
        self.x = value

    def __setitem__(self, name: str, value: int) -> None:
        if name == "x":
            self.x = value


def callback(x: int) -> None:
    list(range(2))  # simulate a brief thing


class ConnectSuite:
    def setup(self):
        self.emitter = E()
        self.receiver = R()

    def time_connect(self):
        self.emitter.changed.connect(callback)

    def time_connect_nochecks(self):
        self.emitter.changed.connect(callback, check_nargs=False, check_types=False)

    def time_connect_checktype(self):
        self.emitter.changed.connect(callback, check_nargs=True, check_types=True)

    def time_connect_method(self):
        self.emitter.changed.connect(self.receiver.method)

    def time_connect_partial(self):
        self.emitter.changed.connect(partial(callback))

    def time_connect_partial_method(self):
        self.emitter.changed.connect(partial(self.receiver.method2, y=1))

    def time_connect_lambda(self):
        self.emitter.changed.connect(lambda x: None)

    def time_connect_builtin(self):
        self.emitter.changed.connect(print)


class EmitSuite:
    params = [1, 10, 70]

    def setup(self, n: int) -> None:
        self.receiver = R()

        self.emitter1: E = E()
        for _ in range(n):
            self.emitter1.changed.connect(callback, unique=False)

        self.emitter2 = E()
        for _ in range(n):
            self.emitter2.changed.connect(self.receiver.method, unique=False)

        # not sure the best way to mark APIs that won't work with older commits
        self.emitter3 = E()
        if hasattr(self.emitter3.changed, "connect_setattr"):
            for _ in range(n):
                self.emitter3.changed.connect_setattr(self.receiver, "attr")

        self.emitter4 = E()
        for _ in range(n):
            self.emitter4.changed.connect(callback, unique=False)
            self.emitter4.changed.connect(self.receiver.method, unique=False)

        self.emitter5 = E()
        if hasattr(self.emitter5.changed, "connect_setitem"):
            for _ in range(n):
                self.emitter5.changed.connect_setitem(self.receiver, "x")

        self.emitter6 = E()
        for _ in range(n):
            self.emitter6.changed.connect(
                partial(self.receiver.method2, y=1), unique=False
            )

    def time_emit_to_function(self, n: int) -> None:
        self.emitter1.changed.emit(1)

    def time_emit_to_method(self, n: int) -> None:
        self.emitter2.changed.emit(1)

    def time_emit_to_attr(self, n: int) -> None:
        self.emitter3.changed.emit(1)

    def time_emit_to_all(self, n: int) -> None:
        self.emitter4.changed.emit(1)

    def time_emit_to_item(self, n: int) -> None:
        self.emitter5.changed.emit(1)

    def time_emit_to_partial(self, n: int) -> None:
        self.emitter6.changed.emit(1)


class EventedModelSuite:
    params = [10, 100]

    def setup(self, n: int) -> None:
        try:
            from psygnal import EventedModel
        except ImportError:
            self.model = None
            return

        class Model(EventedModel):
            x: int = 1

        self.model = Model

    def time_setattr_no_connections(self, n: int) -> None:
        if self.model is None:
            return

        obj = self.model()
        for i in range(n):
            obj.x = i

    def time_setattr_with_connections(self, n: int) -> None:
        if self.model is None:
            return

        obj = self.model()
        obj.events.x.connect(callback)
        for i in range(n):
            obj.x = i
