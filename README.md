# psygnal

[![License](https://img.shields.io/pypi/l/psygnal.svg?color=green)](https://github.com/tlambert03/psygnal/raw/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/psygnal.svg?color=green)](https://pypi.org/project/psygnal)
[![Python Version](https://img.shields.io/pypi/pyversions/psygnal.svg?color=green)](https://python.org)
[![tests](https://github.com/tlambert03/psygnal/workflows/tests/badge.svg)](https://github.com/tlambert03/psygnal/actions)
[![codecov](https://codecov.io/gh/tlambert03/psygnal/branch/master/graph/badge.svg)](https://codecov.io/gh/tlambert03/psygnal)

Pure python implementation of Qt-style Signals

## Quickstart

### install

```sh
pip install psygnal
```

### basic usage

```py
from psygnal import Signal

# create an object with class attribute Signals
class MyObj:

    # this signal will emit a single string
    value_changed = Signal(str)

    def __init__(self, value=0):
        self._value = value

    def set_value(self, value):
        if value != self._value:
            self._value = str(value)
        # emit the signal
        self.value_changed.emit(self._value)

def on_value_changed(new_value):
    print(f"The new value is {new_value!r}")

# instantiate the object with Signals
obj = MyObj()

# connect one or more callbacks
obj.value_changed.connect(on_value_changed)

# callbacks are called when value changes
obj.set_value('hello!')  # prints: 'The new value is 'hello!'
```

### as a decorator

`.connect()` returns the object that it is passed, and so
can be used as a decorator.

```py
@obj.value_changed.connect
def some_other_callback(value):
    print(f"I also received: {value!r}")

obj.set_value('world!')
# prints:
# The new value is 'world!'
# I also received: 'world!'
```

### connection safety (number of arguments)

`psygnal` prevents you from connecting a callback function that is ***guaranteed
to fail*** due to an incompatible number of positional arguments.  For example,
the following callback has too many arguments for our Signal (which we declared above as emitting a single argument: `Signal(str)`)

```py
def i_require_two_arguments(first, second):
    print(first, second)

obj.value_changed.connect(i_require_two_arguments)
```

raises:

```py
ValueError: Cannot connect slot 'i_require_two_arguments' with signature: (first, second):
- Slot requires at least 2 positional arguments, but spec only provides 1

Accepted signature: (p0: str, /)
```

<small><em>
Note: Positional argument checking can be disabled with <code>connect(...,
check_nargs=False)</code>
</em></small>

### connection safety (types)

For type safety when connecting slots, use `check_types=True` when connecting a callback.  Recall that our signal was declared as accepting a string `Signal(str)`.  The following function has an incompatible type annotation: `x: int`.

```py
# this would fail because you cannot concatenate a string and int
def i_expect_an_integer(x: int):
    print(f'{x} + 4 = {x + 4}')

# psygnal won't let you connect it
obj.value_changed.connect(i_expect_an_integer, check_types=True)
```

raises:

```py
ValueError: Cannot connect slot 'i_expect_an_integer' with signature: (x: int):
- Slot types (x: int) do not match types in signal.

Accepted signature: (p0: str, /)
```

<small><em>
Note: unlike Qt, `psygnal` does <strong>not</strong> perform any type coercion
when emitting a value.
</em></small>

## Other similar libraries

### PySignal (deprecated)

This package borrows inspiration from – and is most similar to – the now deprecated [PySignal](https://github.com/dgovil/PySignal) project, with a few notable new features in `psygnal` regarding signature and type checking, sender querying, and threading.

#### similarities with `PySignal`

- still a "Qt-style" signal implementation that doesn't depend on Qt
- supports class methods, functions, lambdas and partials

#### differences with `PySignal`

- the class attribute `pysignal.ClassSignal` is called simply `Signal` in `psygnal` (to more closely match the PyQt/Pyside syntax).  Correspondingly `pysignal.Signal` is similar to `psygnal.SignalInstance`.
- Whereas `PySignal` refrained from doing any signature and/or type checking
  either at slot-connection time, or at signal emission time, `psygnal` offers
  signature declaration similar to Qt with , for example, `Signal(int, int)`.
  along with opt-in signature compatibility (with `check_nargs=True`) and type
  checking (with `check_types=True`). `.connect(..., check_nargs=True)` in
  particular ensures that any slot to connected to a signal will at least be
  compatible with the emitted arguments.
- You *can* query the sender in `psygnal` by using the `Signal.sender()` or `Signal.current_emitter()` class methods. (The former returns the *instance* emitting the signal, similar to Qt's [`QObject.sender()`](https://doc.qt.io/qt-5/qobject.html#sender) method, whereas the latter returns the currently emitting `SignalInstance`.)
- There is basic threading support (calling all slots in another thread), using `emit(..., asynchronous=True)`.  This is experimental, and while thread-safety is the goal, it is not guaranteed.
- There are no `SignalFactory` classes here.
