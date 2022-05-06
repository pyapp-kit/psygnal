# Home

Psygnal (pronounced "signal") is a pure python implementation of
[Qt-style Signals](https://doc.qt.io/qt-5/signalsandslots.html) with
(optional) signature and type checking, and support for threading.

!!! important

    This library does ***not*** require or use Qt. It simply implements a
    similar pattern of inter-object communication with loose coupling.

## Install

```sh
pip install psygnal
```

## Usage

A very simple example:

```python
from psygnal import Signal

class MyObject:
    value_changed = Signal(str)
    shutting_down = Signal()
```

Please see the [Basic Usage](usage) guide for an overview on how to use psygnal,
or the [API Reference](API) for details on a specific class or method.
