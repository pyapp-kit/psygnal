# Testing with `psygnal`

If you would like to test to ensure that signals are emitted (or not emitted) as
expected, you can use the convenience functions in the
[`psygnal.testing`][psygnal.testing] module.

## Examples

The easiest approach is to use one of the `assert_*` context
managers.  These temporarily listen to a signal and check if it is
emitted (or not emitted) when the context is exited.  The API
closely mirrors the [`unittest.mock`][unittest.mock.Mock.assert_called] API,
with the word "called" replaced with "emitted".

```python
from psygnal import Signal
import psygnal.testing as pt

class MyObject:
    changed = Signal()
    value_changed = Signal(int)

def test_my_object():
    obj = MyObject()

    with pt.assert_emitted(obj.changed):
        obj.changed.emit()
    
    with pt.assert_not_emitted(obj.value_changed):
        obj.changed.emit()
    
    with pt.assert_emitted_once(obj.value_changed):
        obj.value_changed.emit(42)

    with pt.assert_emitted_once_with(obj.value_changed, 42):
        obj.value_changed.emit(42)

    with pt.assert_ever_emitted_with(obj.value_changed, 42):
        obj.value_changed.emit(41)
        obj.value_changed.emit(42)
        obj.value_changed.emit(43)
```

All of the context managers yield an instance of
[`SignalTester`][psygnal.testing.SignalTester], which can be used to check the
number of emissions and the arguments. It may also be used directly:

```python
from psygnal import Signal
import psygnal.testing as pt

class MyObject:
    value_changed = Signal(int)

def test_my_object():
    obj = MyObject()
    tester = pt.SignalTester(obj.value_changed)

    with tester:
        obj.value_changed.emit(42)
        obj.value_changed.emit(43)

    assert tester.emit_count == 2
    assert tester.emit_args_list == [(42,), (43,)]
    assert tester.emit_args == (43,)
    tester.assert_ever_emitted_with(42)
    tester.assert_emitted_with(43)
```

See API documentation for
[`SignalTester`][psygnal.testing.SignalTester] for more details.
