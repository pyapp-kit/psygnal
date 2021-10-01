import gc
import time
import weakref
from inspect import Signature
from types import FunctionType
from typing import Optional
from unittest.mock import MagicMock

import pytest

from psygnal import Signal, SignalInstance


# fmt: off
class Emitter:
    no_arg = Signal()
    one_int = Signal(int)
    two_int = Signal(int, int)
    str_int = Signal(str, int)
    no_check = Signal(str, check_nargs_on_connect=False, check_types_on_connect=False)


class MyObj:
    def f_no_arg(self): ...
    def f_str_int_vararg(self, a: str, b: int, *c): ...
    def f_str_int_any(self, a: str, b: int, c): ...
    def f_str_int_kwarg(self, a: str, b: int, c=None): ...
    def f_str_int(self, a: str, b: int): ...
    def f_str_any(self, a: str, b): ...
    def f_str(self, a: str): ...
    def f_int(self, a: int): ...
    def f_any(self, a): ...
    def f_int_int(self, a: int, b: int): ...
    def f_str_str(self, a: str, b: str): ...
    def f_arg_kwarg(self, a, b=None): ...
    def f_vararg(self, *a): ...
    def f_vararg_varkwarg(self, *a, **b): ...
    def f_vararg_kwarg(self, *a, b=None): ...


def f_no_arg(): ...
def f_str_int_vararg(a: str, b: int, *c): ...
def f_str_int_any(a: str, b: int, c): ...
def f_str_int_kwarg(a: str, b: int, c=None): ...
def f_str_int(a: str, b: int): ...
def f_str_any(a: str, b): ...
def f_str(a: str): ...
def f_int(a: int): ...
def f_any(a): ...
def f_int_int(a: int, b: int): ...
def f_str_str(a: str, b: str): ...
def f_arg_kwarg(a, b=None): ...
def f_vararg(*a): ...
def f_vararg_varkwarg(*a, **b): ...
def f_vararg_kwarg(*a, b=None): ...

class MyReceiver:
    expect_signal = None
    expect_sender = None
    expect_name = None

    def assert_sender(self, *a):
        assert Signal.current_emitter() is self.expect_signal
        assert self.expect_name in repr(Signal.current_emitter())
        assert Signal.current_emitter().instance is self.expect_sender
        assert Signal.sender() is self.expect_sender
        assert Signal.current_emitter()._name is self.expect_name

    def assert_not_sender(self, *a):
        # just to make sure we're actually calling it
        assert Signal.current_emitter().instance is not self.expect_sender
# fmt: on


def test_basic_signal():
    """standard Qt usage, as class attribute"""
    emitter = Emitter()
    mock = MagicMock()
    emitter.one_int.connect(mock)
    emitter.one_int.emit(1)
    mock.assert_called_once_with(1)
    mock.reset_mock()

    # calling directly also works
    emitter.one_int(1)
    mock.assert_called_once_with(1)


def test_decorator():
    emitter = Emitter()

    @emitter.one_int.connect
    def boom(v: int):
        raise ValueError

    @emitter.one_int.connect(check_nargs=False)
    def bad_cb(a, b, c):
        ...

    with pytest.raises(ValueError):
        emitter.one_int.emit(1)


def test_misc():
    emitter = Emitter()
    assert isinstance(Emitter.one_int, Signal)
    assert isinstance(emitter.one_int, SignalInstance)

    with pytest.raises(AttributeError):
        emitter.one_int.asdf

    with pytest.raises(AttributeError):
        emitter.one_int.asdf


def test_getattr():
    s = Signal()
    with pytest.raises(AttributeError):
        s.not_a_thing


def test_signature_provided():
    s = Signal(Signature())
    assert s.signature == Signature()

    with pytest.warns(UserWarning):
        s = Signal(Signature(), 1)


def test_emit_checks():
    emitter = Emitter()

    emitter.one_int.emit(check_nargs=False)
    emitter.one_int.emit()
    with pytest.raises(TypeError):
        emitter.one_int.emit(check_nargs=True)

    emitter.one_int.emit(1)

    emitter.one_int.emit(1, 2, check_nargs=False)
    emitter.one_int.emit(1, 2)
    with pytest.raises(TypeError):
        emitter.one_int.emit(1, 2, check_nargs=True)

    with pytest.raises(TypeError):
        emitter.one_int.emit("sdr", check_types=True)

    emitter.one_int.emit("sdr", check_types=False)


def test_basic_signal_blocked():
    """standard Qt usage, as class attribute"""
    emitter = Emitter()
    mock = MagicMock()

    emitter.one_int.connect(mock)
    emitter.one_int.emit(1)
    mock.assert_called_once_with(1)

    mock.reset_mock()
    with emitter.one_int.blocked():
        emitter.one_int.emit(1)
    mock.assert_not_called()


def test_disconnect():
    emitter = Emitter()
    mock = MagicMock()
    with pytest.raises(ValueError) as e:
        emitter.one_int.disconnect(mock, missing_ok=False)
    assert "slot is not connected" in str(e)
    emitter.one_int.disconnect(mock)

    emitter.one_int.connect(mock)
    emitter.one_int.emit(1)
    mock.assert_called_once_with(1)

    mock.reset_mock()
    emitter.one_int.disconnect(mock)
    emitter.one_int.emit(1)
    mock.assert_not_called()


def test_slot_types():
    emitter = Emitter()
    assert len(emitter.one_int._slots) == 0
    emitter.one_int.connect(lambda x: None)
    assert len(emitter.one_int._slots) == 1

    emitter.one_int.connect(f_int)
    assert len(emitter.one_int._slots) == 2
    # connecting same function twice is (currently) OK
    emitter.one_int.connect(f_int)
    assert len(emitter.one_int._slots) == 3
    assert isinstance(emitter.one_int._slots[-1][0], FunctionType)

    # bound methods
    obj = MyObj()
    emitter.one_int.connect(obj.f_int)
    assert len(emitter.one_int._slots) == 4
    assert isinstance(emitter.one_int._slots[-1][0], tuple)
    assert isinstance(emitter.one_int._slots[-1][0][0], weakref.ref)

    with pytest.raises(TypeError):
        emitter.one_int.connect("not a callable")  # type: ignore


def test_basic_signal_with_sender_receiver():
    """standard Qt usage, as class attribute"""
    emitter = Emitter()
    receiver = MyReceiver()
    receiver.expect_sender = emitter
    receiver.expect_signal = emitter.one_int
    receiver.expect_name = "one_int"

    assert Signal.current_emitter() is None
    emitter.one_int.connect(receiver.assert_sender)
    emitter.one_int.emit(1)

    # back to none after the call is over.
    assert Signal.current_emitter() is None
    emitter.one_int.disconnect()

    # sanity check... to make sure that methods are in fact being called.
    emitter.one_int.connect(receiver.assert_not_sender)
    with pytest.raises(AssertionError):
        emitter.one_int.emit(1)


def test_basic_signal_with_sender_nonreceiver():
    """standard Qt usage, as class attribute"""

    emitter = Emitter()
    nr = MyObj()

    emitter.one_int.connect(nr.f_no_arg)
    emitter.one_int.connect(nr.f_int)
    emitter.one_int.connect(nr.f_vararg_varkwarg)
    emitter.one_int.emit(1)

    # emitter.one_int.connect(nr.two_int)


def test_signal_instance():
    """make a signal instance without a class"""
    signal = SignalInstance((int,))
    mock = MagicMock()
    signal.connect(mock)
    signal.emit(1)
    mock.assert_called_once_with(1)

    signal = SignalInstance()
    mock = MagicMock()
    signal.connect(mock)
    signal.emit()
    mock.assert_called_once_with()


def test_signal_instance_error():
    """without a class"""
    signal = Signal()
    mock = MagicMock()
    with pytest.raises(AttributeError) as e:
        signal.connect(mock)
    assert "Signal() class attribute" in str(e)


def test_weakrefs():
    """Test that connect an instance method doesn't hold strong ref."""
    emitter = Emitter()
    obj = MyObj()

    assert len(emitter.one_int) == 0
    emitter.one_int.connect(obj.f_no_arg)
    assert len(emitter.one_int) == 1
    del obj
    gc.collect()
    emitter.one_int.emit(1)  # this should trigger deletion
    assert len(emitter.one_int) == 0


def test_norm_slot():
    e = Emitter()
    r = MyObj()

    normed1 = e.one_int._normalize_slot(r.f_any)
    normed2 = e.one_int._normalize_slot(normed1)
    normed3 = e.one_int._normalize_slot((r, "f_any"))
    normed3 = e.one_int._normalize_slot((weakref.ref(r), "f_any"))
    assert normed1 == (weakref.ref(r), "f_any")
    assert normed1 == normed2 == normed3

    assert e.one_int._normalize_slot(f_any) == f_any


ALL = {n for n, f in locals().items() if callable(f) and n.startswith("f_")}
COUNT_INCOMPATIBLE = {
    "no_arg": ALL - {"f_no_arg", "f_vararg", "f_vararg_varkwarg", "f_vararg_kwarg"},
    "one_int": {
        "f_int_int",
        "f_str_any",
        "f_str_int_any",
        "f_str_int_kwarg",
        "f_str_int_vararg",
        "f_str_int",
        "f_str_str",
    },
    "str_int": {"f_str_int_any"},
}

SIG_INCOMPATIBLE = {
    "no_arg": {"f_int_int", "f_int", "f_str_int_any", "f_str_str"},
    "one_int": {
        "f_int_int",
        "f_str_int_any",
        "f_str_int_vararg",
        "f_str_str",
        "f_str_str",
        "f_str",
    },
    "str_int": {"f_int_int", "f_int", "f_str_int_any", "f_str_str"},
}


@pytest.mark.parametrize("typed", ["typed", "untyped"])
@pytest.mark.parametrize("func_name", ALL)
@pytest.mark.parametrize("sig_name", ["no_arg", "one_int", "str_int"])
@pytest.mark.parametrize("mode", ["func", "meth", "partial"])
def test_connect_validation(func_name, sig_name, mode, typed):
    from functools import partial

    if mode == "meth":
        func = getattr(MyObj(), func_name)
    elif mode == "partial":
        func = partial(globals()[func_name])
    else:
        func = globals()[func_name]
    e = Emitter()

    check_types = typed == "typed"
    signal: SignalInstance = getattr(e, sig_name)
    bad_count = COUNT_INCOMPATIBLE[sig_name]
    bad_sig = SIG_INCOMPATIBLE[sig_name]
    if func_name in bad_count or check_types and func_name in bad_sig:
        with pytest.raises(ValueError) as er:
            signal.connect(func, check_types=check_types)
        assert "Accepted signature:" in str(er)
        return

    signal.connect(func, check_types=check_types)

    args = (p.annotation() for p in signal.signature.parameters.values())
    signal.emit(*args)


def test_connect_lambdas():
    e = Emitter()
    assert len(e.two_int._slots) == 0
    e.two_int.connect(lambda: None)
    e.two_int.connect(lambda x: None)
    assert len(e.two_int._slots) == 2
    e.two_int.connect(lambda x, y: None)
    e.two_int.connect(lambda x, y, z=None: None)
    assert len(e.two_int._slots) == 4
    e.two_int.connect(lambda x, y, *z: None)
    e.two_int.connect(lambda *z: None)
    assert len(e.two_int._slots) == 6
    e.two_int.connect(lambda *z, **k: None)
    assert len(e.two_int._slots) == 7

    with pytest.raises(ValueError):
        e.two_int.connect(lambda x, y, z: None)


def test_mock_connect():
    e = Emitter()
    e.one_int.connect(MagicMock())


# fmt: off
class TypeA: ...
class TypeB(TypeA): ...
class TypeC(TypeB): ...
class Rcv:
    def methodA(self, obj: TypeA): ...
    def methodA_ref(self, obj: 'TypeA'): ...
    def methodB(self, obj: TypeB): ...
    def methodB_ref(self, obj: 'TypeB'): ...
    def methodOptB(self, obj: Optional[TypeB]): ...
    def methodOptB_ref(self, obj: 'Optional[TypeB]'): ...
    def methodC(self, obj: TypeC): ...
    def methodC_ref(self, obj: 'TypeC'): ...
class Emt:
    signal = Signal(TypeB)
# fmt: on


def test_forward_refs_type_checking():
    e = Emt()
    r = Rcv()
    e.signal.connect(r.methodB, check_types=True)
    e.signal.connect(r.methodB_ref, check_types=True)
    e.signal.connect(r.methodOptB, check_types=True)
    e.signal.connect(r.methodOptB_ref, check_types=True)
    e.signal.connect(r.methodC, check_types=True)
    e.signal.connect(r.methodC_ref, check_types=True)

    # signal is emitting a TypeB, but method is expecting a typeA
    assert not issubclass(TypeA, TypeB)
    # typeA is not a TypeB, so we get an error

    with pytest.raises(ValueError):
        e.signal.connect(r.methodA, check_types=True)
    with pytest.raises(ValueError):
        e.signal.connect(r.methodA_ref, check_types=True)


def test_checking_off():
    e = Emitter()

    # the no_check signal was instantiated with check_[nargs/types] = False
    @e.no_check.connect
    def bad_in_many_ways(x: int, y, z):
        ...


def test_keyword_only_not_allowed():
    e = Emitter()

    def f(a: int, *, b: int):
        ...

    with pytest.raises(ValueError) as er:
        e.two_int.connect(f)
    assert "Required KEYWORD_ONLY parameters not allowed" in str(er)


def test_unique_connections():
    e = Emitter()
    assert len(e.one_int._slots) == 0

    e.one_int.connect(f_no_arg, unique=True)
    assert len(e.one_int._slots) == 1

    e.one_int.connect(f_no_arg, unique=True)
    assert len(e.one_int._slots) == 1

    with pytest.raises(ValueError):
        e.one_int.connect(f_no_arg, unique="raise")
    assert len(e.one_int._slots) == 1

    e.one_int.connect(f_no_arg)
    assert len(e.one_int._slots) == 2


def test_asynchronous_emit():
    e = Emitter()
    a = []

    def slow_append(arg: int):
        time.sleep(0.1)
        a.append(arg)

    mock = MagicMock(wraps=slow_append)
    e.no_arg.connect(mock, unique=False)

    assert not Signal.current_emitter()
    value = 42
    thread = e.no_arg.emit(value, asynchronous=True)
    mock.assert_called_once()
    assert Signal.current_emitter() is e.no_arg

    # dude, you have to wait.
    assert not a

    if thread:
        thread.join()
    assert a == [value]
    assert not Signal.current_emitter()


def test_sig_unavailable():
    """In some cases, signature.inspect() fails on a callable, (many builtins).

    We should still connect, but with a warning.
    """
    e = Emitter()
    with pytest.warns(None):
        e.one_int.connect(vars, check_nargs=False)  # no warning

    with pytest.warns(UserWarning):
        e.one_int.connect(vars)

    # we've special cased print... due to frequency of use.
    with pytest.warns(None):
        e.one_int.connect(print)  # no warning
