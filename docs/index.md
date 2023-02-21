# Overview

Psygnal (pronounced "signal") is a pure python implementation of the [observer
pattern](https://en.wikipedia.org/wiki/Observer_pattern) with the API of
[Qt-style Signals](https://doc.qt.io/qt-5/signalsandslots.html) with (optional)
signature and type checking, and support for threading.

!!! important

    This library does ***not*** require or use Qt in any way.
    It simply implements a similar observer pattern API.

## Quickstart

The [observer pattern](https://en.wikipedia.org/wiki/Observer_pattern) is a software design pattern in which an object maintains a list of its dependents ("**observers**"), and notifies them of any state changes – usually by calling a **callback function** provided by the observer.

Here is a simple example of using psygnal:

```python
from psygnal import Signal

class MyObject:
    # define one or signals as class attributes
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

Please see the [Basic Usage](usage.md) guide for an overview on how to use psygnal,
or the [API Reference](API/index.md) for details on a specific class or method.

### Features

In addition to the `Signal` object, psygnal contains:

- a method to convert standard dataclasses (or `attrs`, `pydantic`, or `msgspec`
  objects) into [evented dataclasses](dataclasses.md) that emit signals when
  fields change.
- a number of ["evented" versions of mutable python
  containers](API/containers.md)
- an ["evented" pydantic model](API/model.md) that emits signals whenever a
  model field changes
- [throttling/debouncing](API/throttler.md) decorators
- an experimental ["evented object proxy"](API/proxy.md)
- a few other [utilities](API/utilities.md) for dealing with events.

## Installation

from pip:

```sh
pip install psygnal
```

from conda:

```sh
conda install -c conda-forge psygnal
```

## Performance and Compiled Code

**Performance** is a high priority, as signals are often emitted frequently,
[benchmarks](https://pyapp-kit.github.io/psygnal/) are routinely measured and
[tested during ci](https://codspeed.io/pyapp-kit/psygnal).

Code is compiled using [mypyc](https://mypyc.readthedocs.io/en/latest/index.html).

!!! tip

    To run psygnal *without* using the compiled code, run:

    ```bash
    python -c "import psygnal.utils; psygnal.utils.decompile()"
    ```

    To return the compiled version, run:

    ```bash
    python -c "import psygnal.utils; psygnal.utils.recompile()"
    ```

    *These commands rename the compiled files, and require write
    permissions to the psygnal source directory*
