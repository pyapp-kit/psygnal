# type: ignore
import math
from functools import partial

from psygnal import Signal, SignalInstance
from psygnal.containers import EventedSet


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


def empty(event):
    pass


def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


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
                self.emitter3.changed.connect_setattr(self.receiver, "attr", maxargs=1)

        self.emitter4 = E()
        for _ in range(n):
            self.emitter4.changed.connect(callback, unique=False)
            self.emitter4.changed.connect(self.receiver.method, unique=False)

        self.emitter5 = E()
        if hasattr(self.emitter5.changed, "connect_setitem"):
            for _ in range(n):
                self.emitter5.changed.connect_setitem(self.receiver, "x", maxargs=1)

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
        self.model_instance = Model()

    def time_setattr_no_connections(self, n: int) -> None:
        if self.model is None:
            return

        obj = self.model_instance
        for i in range(n):
            obj.x = i

    def time_setattr_with_connections(self, n: int) -> None:
        if self.model is None:
            return

        obj = self.model_instance
        obj.events.x.connect(callback)
        for i in range(n):
            obj.x = i


class EventedModelWithPropsSuite:
    def setup(self) -> None:
        try:
            import pydantic

            from psygnal import EventedModel

            PYDANTIC_V1 = pydantic.version.VERSION.startswith("1")
        except ImportError:
            self.model = None
            return

        class ModelWithProperties(EventedModel):
            a: int = 3
            b: float = 2.0
            c: int = 3

            @property
            def d(self):
                return (self.c + self.a) ** self.b

            @d.setter
            def d(self, value):
                self.c = value
                self.a = value
                self.b = value * 1.1

            @property
            def e(self):
                fca = fibonacci(self.c) + fibonacci(self.a)
                return fca ** fibonacci(math.ceil(self.b))

            @e.setter
            def e(self, v):
                pass

            if PYDANTIC_V1:

                class Config:
                    allow_property_setters = True
                    field_dependencies = {"e": ["a", "b", "c"]}

            else:
                model_config = {
                    "allow_property_setters": True,
                    "field_dependencies": {"e": ["a", "b", "c"]},
                }

        self.model = ModelWithProperties()
        self.model.events.a.connect(empty)
        self.model.events.b.connect(empty)
        self.model.events.c.connect(empty)
        self.model.events.e.connect(empty)

    def time_event_firing(self) -> None:
        self.model.d = 4
        self.model.d = 18

    def time_long_connection(self) -> None:
        def long_connection(val):
            for _i in range(5):
                fibonacci(self.model.c)

        self.model.events.e.connect(long_connection)
        self.model.d = 15


class EventedSetSuite:
    params = [10, 100000]

    def setup(self, n):
        self.my_set = EventedSet(range(n))

    def time_create_set(self, n):
        EventedSet(range(n))

    def time_update_new(self, n):
        self.my_set.update(range(n, n * 2))

    def time_update_existing(self, n):
        self.my_set.update(range(n))

    def time_update_overlap(self, n):
        self.my_set.update(range(n // 2, n + n // 2))

    def time_clear(self, _):
        self.my_set.clear()


class EventedSetWithCallbackSuite(EventedSetSuite):
    def setup(self, n):
        super().setup(n)
        self.my_set.events.items_changed.connect(callback)
