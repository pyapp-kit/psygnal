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
    def method(self, x: int):
        ...

    def method2(self, x: int, y: int):
        ...


def callback(x: int):
    pass


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
    params = [1, 10, 100]

    def setup(self, n):
        self.emitter = E()
        for _ in range(n):
            self.emitter.changed.connect(callback, unique=False)

    def time_emit(self, n):
        self.emitter.changed.emit(1)
