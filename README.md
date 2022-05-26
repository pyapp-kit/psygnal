# psygnal

[![License](https://img.shields.io/pypi/l/psygnal.svg?color=green)](https://github.com/tlambert03/psygnal/raw/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/psygnal.svg?color=green)](https://pypi.org/project/psygnal)
![Conda](https://img.shields.io/conda/v/conda-forge/psygnal)
[![Python Version](https://img.shields.io/pypi/pyversions/psygnal.svg?color=green)](https://python.org)
[![CI](https://github.com/tlambert03/psygnal/actions/workflows/ci.yml/badge.svg)](https://github.com/tlambert03/psygnal/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/tlambert03/psygnal/branch/main/graph/badge.svg?token=qGnz9GXpEb)](https://codecov.io/gh/tlambert03/psygnal)

Psygnal (pronounced "signal") is a pure python implementation of
[Qt-style Signals](https://doc.qt.io/qt-5/signalsandslots.html) with
(optional) signature and type checking, and support for threading.


> Note: this library does _not_ require Qt. It just implements a similar pattern of inter-object communication with loose coupling.

## Documentation

https://psygnal.readthedocs.io/

### Install

```sh
pip install psygnal
```

```sh
conda install -c conda-forge psygnal
```

## Usage

A very simple example:

```python
from psygnal import Signal

class MyObject:
    value_changed = Signal(str)
    shutting_down = Signal()

my_obj = MyObject()

@my_obj.value_changed.connect
def on_change(new_value: str):
    print(f"The value changed to {new_value}!")

my_obj.value_changed.emit('hi')
```

Much more detail available in the [documentation](https://psygnal.readthedocs.io/)!

## Alternatives

There are other libraries that implement similar event-based signals, they may
server your purposes better depending on what you are doing.

### [PySignal](https://github.com/dgovil/PySignal) (deprecated)

This package borrows inspiration from – and is most similar to – the now
deprecated [PySignal](https://github.com/dgovil/PySignal) project, with a few
notable new features in `psygnal` regarding signature and type checking, sender
querying, and threading.

#### similarities with `PySignal`

- still a "Qt-style" signal implementation that doesn't depend on Qt
- supports class methods, functions, lambdas and partials

#### differences with `PySignal`

- the class attribute `pysignal.ClassSignal` is called simply `Signal` in
  `psygnal` (to more closely match the PyQt/Pyside syntax).  Correspondingly
  `pysignal.Signal` is similar to `psygnal.SignalInstance`.
- Whereas `PySignal` refrained from doing any signature and/or type checking
  either at slot-connection time, or at signal emission time, `psygnal` offers
  signature declaration similar to Qt with , for example, `Signal(int, int)`.
  along with opt-in signature compatibility (with `check_nargs=True`) and type
  checking (with `check_types=True`). `.connect(..., check_nargs=True)` in
  particular ensures that any slot to connected to a signal will at least be
  compatible with the emitted arguments.
- You *can* query the sender in `psygnal` by using the `Signal.sender()` or
  `Signal.current_emitter()` class methods. (The former returns the *instance*
  emitting the signal, similar to Qt's
  [`QObject.sender()`](https://doc.qt.io/qt-5/qobject.html#sender) method,
  whereas the latter returns the currently emitting `SignalInstance`.)
- There is basic threading support (calling all slots in another thread), using
  `emit(..., asynchronous=True)`.  This is experimental, and while thread-safety
  is the goal, it is not guaranteed.
- There are no `SignalFactory` classes here.

*The following two libraries implement django-inspired signals, they do not
attempt to mimic the Qt API.*

### [Blinker](https://github.com/jek/blinker)

Blinker provides a fast dispatching system that allows any number of interested
parties to subscribe to events, or "signals".

### [SmokeSignal](https://github.com/shaunduncan/smokesignal/)

(This appears to be unmaintained)

## Benchmark history

https://www.talleylambert.com/psygnal/

## Developers

### Debugging

While `psygnal` is a pure python module, it is compiled with Cython to increase
performance.  To import `psygnal` in uncompiled mode, without deleting the
shared library files from the psyngal module, set the environment variable
`PSYGNAL_UNCOMPILED` before importing psygnal.  The `psygnal._compiled` variable
will tell you if you're running the compiled library or not.
