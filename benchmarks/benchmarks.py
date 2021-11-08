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

    @property
    def attr(self):
        return

    @attr.setter
    def attr(self, value):
        return


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
        self.receiver = R()

        self.emitter1 = E()
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

    def time_emit_to_function(self, n):
        self.emitter1.changed.emit(1)

    def time_emit_to_method(self, n):
        self.emitter2.changed.emit(1)

    def time_emit_to_attr(self, n):
        self.emitter3.changed.emit(1)

    def time_emit_to_all(self, n):
        self.emitter4.changed.emit(1)
