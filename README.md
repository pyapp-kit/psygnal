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

### Evented Dataclasses

A particularly nice usage of the signal pattern is to emit signals whenever a
field of a dataclass changes. Psygnal provides an `@evented` decorator that will
emit a signal whenever a field changes.  It is compatible with `dataclasses`
from [the standard library](https://docs.python.org/3/library/dataclasses.html),
as well as [attrs](https://www.attrs.org/en/stable/), and
[pydantic](https://pydantic-docs.helpmanual.io):

```python
from psygnal import evented
from dataclasses import dataclass

@evented
@dataclass
class Person:
    name: str
    age: int = 0

person = Person('John', age=30)

# connect callbacks
@person.events.age.connect
def _on_age_change(new_age: str):
    print(f"Age changed to {new_age}")

person.age = 31  # prints: Age changed to 31
```

See the [dataclass documentation](https://psygnal.readthedocs.io/en/latest/dataclasses/) for more details.


## Benchmark history

https://www.talleylambert.com/psygnal/

## Developers

### Debugging

While `psygnal` is a pure python module, it is compiled with Cython to increase
performance.  To import `psygnal` in uncompiled mode, without deleting the
shared library files from the psyngal module, set the environment variable
`PSYGNAL_UNCOMPILED` before importing psygnal.  The `psygnal._compiled` variable
will tell you if you're running the compiled library or not.
