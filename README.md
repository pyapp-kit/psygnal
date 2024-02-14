# psygnal

[![License](https://img.shields.io/pypi/l/psygnal.svg?color=green)](https://github.com/pyapp-kit/psygnal/raw/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/psygnal.svg?color=green)](https://pypi.org/project/psygnal)
[![Conda](https://img.shields.io/conda/v/conda-forge/psygnal)](https://github.com/conda-forge/psygnal-feedstock)
[![Python Version](https://img.shields.io/pypi/pyversions/psygnal.svg?color=green)](https://python.org)
[![CI](https://github.com/pyapp-kit/psygnal/actions/workflows/test.yml/badge.svg)](https://github.com/pyapp-kit/psygnal/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/pyapp-kit/psygnal/branch/main/graph/badge.svg?token=qGnz9GXpEb)](https://codecov.io/gh/pyapp-kit/psygnal)
[![Documentation Status](https://readthedocs.org/projects/psygnal/badge/?version=latest)](https://psygnal.readthedocs.io/en/latest/?badge=latest)
[![Benchmarks](https://img.shields.io/badge/⏱-codspeed-%23FF7B53)](https://codspeed.io/pyapp-kit/psygnal)

Psygnal (pronounced "signal") is a pure python implementation of the [observer
pattern](https://en.wikipedia.org/wiki/Observer_pattern), with the API of
[Qt-style Signals](https://doc.qt.io/qt-5/signalsandslots.html) with (optional)
signature and type checking, and support for threading.

> This library does ***not*** require or use Qt in any way, It simply implements
> a similar observer pattern API.

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

The [observer pattern](https://en.wikipedia.org/wiki/Observer_pattern) is a software design pattern in which an object maintains a list of its dependents ("**observers**"), and notifies them of any state changes – usually by calling a **callback function** provided by the observer.

Here is a simple example of using psygnal:

```python
from psygnal import Signal

class MyObject:
    # define one or more signals as class attributes
    value_changed = Signal(str)

# create an instance
my_obj = MyObject()

# You (or others) can connect callbacks to your signals
@my_obj.value_changed.connect
def on_change(new_value: str):
    print(f"The value changed to {new_value}!")

# The object may now emit signals when appropriate,
# (for example in a setter method)
my_obj.value_changed.emit('hi')  # prints "The value changed to hi!"
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

### Evented Containers

`psygnal.containers` provides evented versions of mutable data structures
(`dict`, `list`, `set`), for cases when you need to monitor mutation:

```python
from psygnal.containers import EventedList

my_list = EventedList([1, 2, 3, 4, 5])

my_list.events.inserted.connect(lambda i, val: print(f"Inserted {val} at index {i}"))
my_list.events.removed.connect(lambda i, val: print(f"Removed {val} at index {i}"))

my_list.append(6)  # Output: Inserted 6 at index 5
my_list.pop()  # Output: Removed 6 at index 5
```

See the
[evented containers documentation](https://psygnal.readthedocs.io/en/latest/API/containers/)
for more details.

## Benchmark history

https://pyapp-kit.github.io/psygnal/

and

https://codspeed.io/pyapp-kit/psygnal

## Developers

### Compiling

While `psygnal` is a pure python package, it is compiled with mypyc to increase
performance.  To test the compiled version locally, you can run:

```bash
make build
```

(which is just an alias for `HATCH_BUILD_HOOKS_ENABLE=1 pip install -e .`)

### Debugging

 To disable all compiled files and run the pure python version,
you may run:

```bash
python -c "import psygnal.utils; psygnal.utils.decompile()"
```

To return the compiled version, run:

```bash
python -c "import psygnal.utils; psygnal.utils.recompile()"
```

The `psygnal._compiled` variable will tell you if you're using the compiled
version or not.
