# Overview

Psygnal (pronounced "signal") is a pure python implementation of
[Qt-style Signals](https://doc.qt.io/qt-5/signalsandslots.html) with
(optional) signature and type checking, and support for threading.

!!! important

    This library does ***not*** require or use Qt in any way.
    It simply implements the [observer pattern](https://en.wikipedia.org/wiki/Observer_pattern): inter-object communication with loose coupling.

**Performance** is a high priority, as signals are often emitted frequently,
[benchmarks](https://www.talleylambert.com/psygnal/) are routinely measured.
Code is compiled using [Cython](https://cython.org/).

!!! tip

    To run psygnal *without* using the compiled cython code, set an
    `PSYGNAL_UNCOMPILED` environment variable to `1`

## Quickstart

A very simple example:

```python
# import psygnal.Signal
from psygnal import Signal

class MyObject:
    # define one or signals as class attributes
    value_changed = Signal(str)
    shutting_down = Signal()

# create an instance
my_obj = MyObject()

# You (or others) can connect callbacks to your signals
@my_obj.value_changed.connect
def on_change(new_value: str):
    print(f"The value changed to {new_value}!")

# you emit signals when appropriate (e.g. when the value changes)
my_obj.value_changed.emit('hi')
```

Please see the [Basic Usage](usage.md) guide for an overview on how to use psygnal,
or the [API Reference](API/index.md) for details on a specific class or method.

In addition to the `Signal` object, psygnal contains:

- an `@evented` decorator that converts standard dataclasses (or attrs, or
  pydantic) into [evented dataclasses](dataclasses.md) that emit signals when
  fields change.
- a number of ["evented" versions of mutable python containers](API/containers.md)
- an ["evented" pydantic model](API/model.md) that emits signals whenever a model field changes
- [throttling/debouncing](API/throttler.md) decorators
- an experimental ["evented object proxy"](API/proxy.md)
- a few other [utilties](API/utilities.md) for dealing with events.

## Installation

from pip:

```sh
pip install psygnal
```

from conda:

```sh
conda install -c conda-forge psygnal
```
