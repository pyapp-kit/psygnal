# Usage

If you are familiar with the Qt [Signals &
Slots](https://doc.qt.io/qt-5/signalsandslots.html) API as implemented in
[PySide](https://wiki.qt.io/Qt_for_Python_Signals_and_Slots) and
[PyQt5](https://www.riverbankcomputing.com/static/Docs/PyQt5/signals_slots.html),
then you should be good to go!  `psygnal` aims to be a superset of those APIs
(some functions do accept additional arguments, like
[`check_nargs`](#connection-safety-number-of-arguments) and
[`check_types`](#connection-safety-types)).

*Note: the name "`Signal`" is used here instead of `pyqtSignal`, following the
`qtpy` and `PySide` convention.*

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

### `connect` as a decorator

`.connect()` returns the object that it is passed, and so
can be used as a decorator.

```py
@obj.value_changed.connect
def some_other_callback(value):
    print(f"I also received: {value!r}")

obj.set_value('world!') # prints: "I also received: 'world!'"
```

### disconnecting callbacks

Callbacks can be disconnected using
[`disconnect`][psygnal.SignalInstance.disconnect]

```python
obj.value_changed.disconnect(on_value_changed)
```

## Connection safety

The [`connect`][psygnal.SignalInstance.connect] method provides
a number of "safety" measures:

### too many arguments

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

### too few arguments

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

### type checking

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

### weak references

psygnal tries very hard not to hold strong references to connected objects.
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

## Querying the sender

Your callback may occasionally need to know which signal
invoked the callback.

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

## Asynchronous signal emission

There is experimental support for calling all connected slots in another
thread, using `emit(..., asynchronous=True)`

```py
obj = MyObj()

def slow_callback(arg):
    import time
    time.sleep(0.5)
    print(f"Hi {arg!r}, from another thread")

obj.value_changed.connect(slow_callback)
```

This one is called synchronously (note the order of print statements):

```py
obj.value_changed.emit('friend')
print("Hi, from main thread.")

# after 0.5 seconds, prints:
# Hi 'friend', from another thread
# Hi, from main thread.
```

This one is called asynchronously, and immediately returns to the caller.
A `threading.Thread` object is returned.

```py
thread = obj.value_changed.emit('friend', asynchronous=True)
print("Hi, from main thread.")

# immediately prints
# Hi, from main thread.

# then after 0.5 seconds this will print:
# Hi 'friend', from another thread
```

**Note:** The user is responsible for `joining` and managing the
`threading.Thread` instance returned when calling `.emit(...,
asynchronous=True)`.

**Experimental!**  While thread-safety is the goal,
([`RLocks`](https://docs.python.org/3/library/threading.html#rlock-objects) are
used during important state mutations) it is not guaranteed.  Please use at your
own risk. Issues/PRs welcome.

## Blocking a signal

To temporarily block a signal, use the `signal.blocked()` context context manager:

```py
obj = MyObj()

with obj.value_changed.blocked():
    # do stuff without obj.value_changed getting emitted
    ...
```

To block/unblock permanently (outside of a context manager), use `signal.block()`
and `signal.unblock()`.

## Pausing a signal

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
