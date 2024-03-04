# Usage

If you are familiar with the Qt [Signals &
Slots](https://doc.qt.io/qt-5/signalsandslots.html) API as implemented in
[PySide](https://wiki.qt.io/Qt_for_Python_Signals_and_Slots) and
[PyQt5](https://www.riverbankcomputing.com/static/Docs/PyQt5/signals_slots.html),
then you should be good to go!  `psygnal` aims to be a superset of those APIs
(some functions do accept additional arguments, like
[`check_nargs`](#connection-safety-number-of-arguments) and
[`check_types`](#connection-safety-types)).

## Creating a Signal

Generally speaking, you will create a [`Signal`][psygnal.Signal] as an
attribute on a class. The arguments passed to the `Signal` constructor
should reflect the types that the signal will *emit*.  For example, if
you want to have a `value_changed` signal, and the type of the value
changing is a [`str`][], then you would create do something like this:

```py
from psygnal import Signal

# define an object with class attribute Signals
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
```

Note how the class itself calls `value_changed.emit` whenever
the value changes. This notifies "anyone listening" that a change
has occurred.

Other components can subscribe to these change notifications by
connecting a callback function to the signal instance using its
[`connect`][psygnal.SignalInstance.connect] method

```python
def on_value_changed(new_value: str):
    print(f"The new value is {new_value!r}")

# instantiate the object with Signals
obj = MyObj()

# connect one or more callbacks with `connect`
obj.value_changed.connect(on_value_changed)

# callbacks are called when value changes
obj.set_value('hello!')  # prints: 'The new value is 'hello!'
```

### Using `connect` as a Decorator

`.connect()` returns the object that it is passed, and so
can be used as a decorator.

```py
@obj.value_changed.connect
def some_other_callback(value):
    print(f"I also received: {value!r}")

obj.set_value('world!') # prints: "I also received: 'world!'"
```

### Disconnecting Callbacks

Callbacks can be disconnected using
[`disconnect`][psygnal.SignalInstance.disconnect]

```python
obj.value_changed.disconnect(on_value_changed)
```

## Connection Safety

The [`connect`][psygnal.SignalInstance.connect] method provides
a number of "safety" measures:

### Too Many Arguments

By default `psygnal` prevents you from connecting a callback function that is
***guaranteed to fail*** due to an incompatible number of positional arguments.
For example, the following callback has too many arguments for our Signal (which
we declared above as emitting a single argument: `Signal(str)`)

```py
def i_require_two_arguments(first, second):
    print(first, second)

obj.value_changed.connect(i_require_two_arguments)
```

raises:

```pytb
ValueError: Cannot connect slot 'i_require_two_arguments'
with signature: (first, second):
- Slot requires at least 2 positional arguments, but spec only provides 1

Accepted signature: (p0: str, /)
```

*Note: Positional argument checking can be disabled with `connect(...,
check_nargs=False)`*

### Too Few Arguments

While a callback may not require *more* positional arguments than the signature
of the `Signal` to which it is connecting, it *may* accept less. Extra arguments
will be discarded when emitting the signal (so it isn't necessary to create a
`lambda` to swallow unnecessary arguments):

```py
obj = MyObj()

def no_args_please():
    print(locals())

obj.value_changed.connect(no_args_please)

# otherwise one might need
# obj.value_changed.connect(lambda a: no_args_please())

obj.value_changed.emit('hi')  # prints: "{}"
```

### Type Checking

For type safety when connecting slots, use `check_types=True` when connecting a
callback.  Recall that our signal was declared as accepting a string
`Signal(str)`.  The following function has an incompatible type annotation: `x:
int`.

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

*Note: unlike Qt, `psygnal` does **not** perform any type coercion when emitting
a value.*

### Weak References

Psygnal tries very hard not to hold strong references to connected objects.
In the simplest case, if you connect a bound method as a callback to a signal
instance:

```python
class T:
    def my_method(self):
        ...

obj = T()
signal.connect(t.my_method)
```

Then there is a risk of `signal` holding a reference to `obj` even after `obj`
has been deleted, preventing garbage collection (and possibly causing errors
when the signal is emitted next).  Psygnal avoids this with weak references. It
goes a bit farther, trying to prevent strong references in these cases as well:

- class methods used as the callable in `functools.partial`
- decorated class methods that mangle the name of the callback.

Another common case for leaking strong references is a `partial` closing on an
object, in order to set an attribute:

```python
class T:
    x = 1

obj = T()
signal.connect(partial(setattr, obj, 'x'))  # ref to obj stuck in the connection
```

Here, psygnal offers the `connect_settatr` convenience method, which reduces code
and helps you avoid leaking strong references to `obj`:

```python
signal.connect_setatttr(obj, 'x')
```

## Querying the Sender

Your callback may occasionally need to know which signal invoked the callback.

Similar to Qt's [`QObject.sender()`](https://doc.qt.io/qt-5/qobject.html#sender)
method, a callback can query the sender using the `Signal.sender()` class
method.  (The implementation is of course different than Qt, since the receiver
is not a `QObject`.)

```py
obj = MyObj()

def curious():
    print("Sent by", Signal.sender())
    assert Signal.sender() == obj

obj.value_changed.connect(curious)
obj.value_changed.emit(10)

# prints (and does not raise):
# Sent by <__main__.MyObj object at 0x1046a30d0>
```

*If you want the actual signal instance that is emitting the signal
(`obj.value_changed` in the above example), use `Signal.current_emitter()`.*

## Connecting across Threads

By default, callbacks connected to signals are invoked immediately when the
signal is emitted, in the same thread that emitted the signal.  This means
that if you emit a signal from a background thread, the callbacks will be
invoked in that background thread:

```py
from threading import Thread, current_thread

obj = MyObj()

@obj.value_changed.connect
def callback(arg):
    print(f"I was called with {arg!r} in {current_thread().name!r}")

Thread(target=obj.value_changed.emit, args=('hi',)).start()
# prints "I was called with 'hi' in 'Thread-1 (emit)'"
```

In some cases, particularly when working with GUI frameworks like Qt, you may
want to ensure that callbacks are invoked in a specific thread (e.g. the main
thread). For this, you can use the `thread` argument to the `connect` method.

It takes a `threading.Thread` instance (or the strings `"main"` or `"current"`,
which are aliases for the main thread and the current thread, respectively),
and will ensure that the callback is invoked in that thread.  This is accomplished
as follows:

1. If the signal is emitted from the same thread as the thread that was passed
   to the `connect(thread=...)` method, then the callback is invoked
   immediately.
2. If the signal is emitted from a different thread, then the callback is added
    to a queue specific to that thread.
3. **Important!**  It is up to the user to ensure that `psygnal.emit_queued()`
   is called in the target thread. Most often, this will be done periodically
   using an event loop (see below, for a convenient way to do this when using
   Qt).

```py
from threading import Thread, current_thread
from psygnal import emit_queued

obj = MyObj()

@obj.value_changed.connect(thread='main')
def callback(arg):
    print(f"I was called with {arg!r} in {current_thread().name!r}")

Thread(target=obj.value_changed.emit, args=('hi',)).start()
# at this point, the callback has not yet been invoked

emit_queued()  # <-- emits anything queued in the thread calling this function
# prints "I was called with 'hi' in 'MainThread'"
```

### Using with Event Loops

Most of the time, you will want to call `psygnal.emit_queued` periodically from
some event loop. Psygnal itself is agnostic to the event loop you are using.
A *very* rudimentary event loop might look like this:

```py
import time

# A simple event loop that just calls emit_queued periodically
def run_loop():
    while True:
        try:
            # do some work
            emit_queued()
            time.sleep(0.1)
        except KeyboardInterrupt:
            break

# something to run in a background thread
def _emit_periodically():
    for i in range(10):
        obj.value_changed.emit("hi")
        time.sleep(0.5)

# start the background thread
Thread(target=_emit_periodically).start()
# start the event loop
run_loop()

# prints "I was called with 'hi' in 'MainThread'" 10 times
```

### Using with Qt

Because Qt is commonly used with psygnal, we provide a convenience
function `psygnal.qt.start_emitting_from_queue` that can be used to start
monitoring the emission queue for a given thread. (It starts a `QTimer` in the
invoking thread that calls `psygnal.emit_queued` periodically).

```py
from threading import Thread, current_thread
from qtpy.QtCore import QCoreApplication
from psygnal.qt import start_emitting_from_queue

obj = MyObj()

@obj.value_changed.connect(thread='main')
def callback(arg):
    print(f"I was called with {arg!r} in {current_thread().name!r}")

app = QCoreApplication([])
start_emitting_from_queue()  # <-- watch for queued signals in the main thread

# emit the signal from a background thread
Thread(target=obj.value_changed.emit, args=('hi',)).start()

app.processEvents()  # or app.exec_(), or anything to keep the event loop running
# prints "I was called with 'hi' in 'MainThread'"
```

It is ok to call `start_emitting_from_queue` multiple times (so multiple
end-users can use it).

## Blocking a Signal

To temporarily block a signal, use the `signal.blocked()` context context manager:

```py
obj = MyObj()

with obj.value_changed.blocked():
    # do stuff without obj.value_changed getting emitted
    ...
```

To block/unblock permanently (outside of a context manager), use `signal.block()`
and `signal.unblock()`.

## Pausing a Signal

Sometimes it is useful to temporarily collect/buffer emission events, and then emit
them together as a single event.  This can be accomplished using the
`signal.pause()`/`signal.resume()` methods, or the `signal.paused()` context manager.

If a function is passed to `signal.paused(func)` (or `signal.resume(func)`) it will
be passed to `functools.reduce` to combine all of the emitted values collected during
the paused period, and a single combined value will be emitted.

```py
obj = MyObj()
obj.value_changed.connect(print)

# note that signal.paused() and signal.resume() accept a reducer function
with obj.value_changed.paused(lambda a,b: (f'{a[0]}_{b[0]}',), ('',)):
    obj.value_changed('a')
    obj.value_changed('b')
    obj.value_changed('c')
# prints '_a_b_c'
```

*NOTE: args passed to `emit` are collected as tuples, so the two arguments
passed to `reducer` will always be tuples. `reducer` must handle that and
return an args tuple.
For example, the three `emit()` events above would be collected as*

```python
[('a',), ('b',), ('c',)]
```

*and would be reduced and re-emitted as follows:*

```python
obj.emit(*functools.reduce(reducer, [('a',), ('b',), ('c',)]))
```

## Exceptions in Callbacks

If an exception is raised in a callback, it will be immediately re-raised as a
`psygnal.EmitLoopError` from the original exception.  The original exception
will be available at the `__cause__` attribute of the `EmitLoopError` and
should appear higher up in the stack trace.

If you would like to *ignore* exceptions that occur in callbacks (e.g. if you
want to make sure that all other connected callbacks are still called), you can
use the `suppress` context manager from the `contextlib` module when emitting
the signal:

```python
from contextlib import suppress
from psygnal import EmitLoopError

with suppress(EmitLoopError):
    obj.emitter.emit(...)
```
