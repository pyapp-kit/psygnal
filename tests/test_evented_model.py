import inspect
from typing import ClassVar, List, Sequence, Union
from unittest.mock import Mock

import numpy as np
import pytest
from typing_extensions import Protocol, runtime_checkable

from psygnal import EventedModel, SignalGroup


def test_creating_empty_evented_model():
    """Test creating an empty evented pydantic model."""
    model = EventedModel()
    assert model is not None
    assert model.events is not None


def test_evented_model():
    """Test creating an evented pydantic model."""

    class User(EventedModel):
        id: int
        name: str = "Alex"
        age: ClassVar[int] = 100

    user = User(id=0)
    # test basic functionality
    assert user.id == 0
    assert user.name == "Alex"

    user.id = 2
    assert user.id == 2

    # test event system
    assert isinstance(user.events, SignalGroup)
    assert "id" in user.events.signals
    assert "name" in user.events.signals

    # ClassVars are excluded from events
    assert "age" not in user.events.signals

    id_mock = Mock()
    name_mock = Mock()
    user.events.id.connect(id_mock)
    user.events.name.connect(name_mock)
    # setting an attribute should, by default, emit an event with the value
    user.id = 4
    id_mock.assert_called_with(4)
    name_mock.assert_not_called()
    # and event should only be emitted when the value has changed.
    id_mock.reset_mock()
    user.id = 4
    id_mock.assert_not_called()
    name_mock.assert_not_called()


def test_evented_model_np_array_equality():
    """Test checking equality with an evented model with direct numpy."""

    class Model(EventedModel):
        values: np.ndarray

        class Config:
            arbitrary_types_allowed = True

    model1 = Model(values=np.array([1, 2, 3]))
    model2 = Model(values=np.array([1, 5, 6]))

    assert model1 == model1
    assert model1 != model2

    model2.values = np.array([1, 2, 3])
    assert model1 == model2


def test_evented_model_da_array_equality():
    """Test checking equality with an evented model with direct dask."""
    da = pytest.importorskip("dask.array")

    class Model(EventedModel):
        values: da.Array

        class Config:
            arbitrary_types_allowed = True

    r = da.ones((64, 64))
    model1 = Model(values=r)
    model2 = Model(values=da.ones((64, 64)))

    assert model1 == model1
    # dask arrays will only evaluate as equal if they are the same object.
    assert model1 != model2

    model2.values = r
    assert model1 == model2


def test_values_updated():
    class User(EventedModel):
        """Demo evented model.

        Parameters
        ----------
        id : int
            User id.
        name : str, optional
            User name.
        """

        id: int
        name: str = "A"
        age: ClassVar[int] = 100

    user1 = User(id=0)
    user2 = User(id=1, name="K")
    # Check user1 and user2 dicts
    assert user1.dict() == {"id": 0, "name": "A"}
    assert user2.dict() == {"id": 1, "name": "K"}

    # Add mocks
    user1_events = Mock()
    u1_id_events = Mock()
    u2_id_events = Mock()
    user1.events.connect(user1_events)
    user1.events.id.connect(u1_id_events)
    user2.events.id.connect(u2_id_events)

    # Update user1 from user2
    user1.update(user2)
    assert user1.dict() == {"id": 1, "name": "K"}

    u1_id_events.assert_called_with(1)
    u2_id_events.assert_not_called()
    assert user1_events.call_count == 2
    u1_id_events.reset_mock()
    u2_id_events.reset_mock()
    user1_events.reset_mock()

    # Update user1 from user2 again, no event emission expected
    user1.update(user2)
    assert user1.dict() == {"id": 1, "name": "K"}

    u1_id_events.assert_not_called()
    u2_id_events.assert_not_called()
    assert user1_events.call_count == 0


def test_update_with_inner_model_union():
    class Inner(EventedModel):
        w: str

    class AltInner(EventedModel):
        x: str

    class Outer(EventedModel):
        y: int
        z: Union[Inner, AltInner]

    original = Outer(y=1, z=Inner(w="a"))
    updated = Outer(y=2, z=AltInner(x="b"))

    original.update(updated, recurse=False)

    assert original == updated


def test_update_with_inner_model_protocol():
    @runtime_checkable
    class InnerProtocol(Protocol):
        def string(self) -> str:
            ...

        # Protocol fields are not successfully set without explicit validation.
        @classmethod
        def __get_validators__(cls):
            yield cls.validate

        @classmethod
        def validate(cls, v):
            return v

    class Inner(EventedModel):
        w: str

        def string(self) -> str:
            return self.w

    class AltInner(EventedModel):
        x: str

        def string(self) -> str:
            return self.x

    class Outer(EventedModel):
        y: int
        z: InnerProtocol

    original = Outer(y=1, z=Inner(w="a"))
    updated = Outer(y=2, z=AltInner(x="b"))

    original.update(updated, recurse=False)

    assert original == updated


def test_evented_model_signature():
    class T(EventedModel):
        x: int
        y: str = "yyy"
        z = b"zzz"

    assert isinstance(T.__signature__, inspect.Signature)
    sig = inspect.signature(T)
    assert str(sig) == "(*, x: int, y: str = 'yyy', z: bytes = b'zzz') -> None"


class MyObj:
    def __init__(self, a: int, b: str) -> None:
        self.a = a
        self.b = b

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_type

    @classmethod
    def validate_type(cls, val):
        # turn a generic dict into object
        if isinstance(val, dict):
            a = val.get("a")
            b = val.get("b")
        elif isinstance(val, MyObj):
            return val
        # perform additional validation here
        return cls(a, b)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def _json_encode(self):
        return self.__dict__


def test_evented_model_serialization():
    class Model(EventedModel):
        """Demo evented model."""

        obj: MyObj

    m = Model(obj=MyObj(1, "hi"))
    raw = m.json()
    assert raw == '{"obj": {"a": 1, "b": "hi"}}'
    deserialized = Model.parse_raw(raw)
    assert deserialized == m


def test_nested_evented_model_serialization():
    """Test that encoders on nested sub-models can be used by top model."""

    class NestedModel(EventedModel):
        obj: MyObj

    class Model(EventedModel):
        nest: NestedModel

    m = Model(nest={"obj": {"a": 1, "b": "hi"}})
    raw = m.json()
    assert raw == r'{"nest": {"obj": {"a": 1, "b": "hi"}}}'
    deserialized = Model.parse_raw(raw)
    assert deserialized == m


def test_evented_model_dask_delayed():
    """Test that evented models work with dask delayed objects"""
    dd = pytest.importorskip("dask.delayed")
    dask = pytest.importorskip("dask")

    class MyObject(EventedModel):
        attribute: dd.Delayed

        class Config:
            arbitrary_types_allowed = True

    @dask.delayed
    def my_function():
        pass

    o1 = MyObject(attribute=my_function)

    # check that equality checking works as expected
    assert o1 == o1


class T(EventedModel):
    a: int = 1
    b: int = 1

    @property
    def c(self) -> List[int]:
        return [self.a, self.b]

    @c.setter
    def c(self, val: Sequence[int]):
        self.a, self.b = val

    class Config:
        allow_property_setters = True
        guess_property_dependencies = True


def test_nnn():
    class MyModel(EventedModel):
        a: int = 1
        b: int = 1

        @property
        def c(self) -> List[int]:
            return [self.a, self.b]

        @c.setter
        def c(self, val: Sequence[int]) -> None:
            self.a, self.b = val

        class Config:
            allow_property_setters = True
            property_dependencies = {"c": ["a", "b"]}

    assert list(MyModel.__property_setters__) == ["c"]
    # the metaclass should have figured out that both a and b affect c
    assert MyModel.__field_dependents__ == {"a": {"c"}, "b": {"c"}}


def test_evented_model_with_property_setters():
    t = T()

    assert list(T.__property_setters__) == ["c"]
    # the metaclass should have figured out that both a and b affect c
    assert T.__field_dependents__ == {"a": {"c"}, "b": {"c"}}

    # all the fields and properties behave as expected
    assert t.c == [1, 1]
    t.a = 4
    assert t.c == [4, 1]
    t.c = [2, 3]
    assert t.c == [2, 3]
    assert t.a == 2
    assert t.b == 3


def test_evented_model_with_property_setters_events():
    t = T()
    assert "c" in t.events.signals  # the setter has an event
    mock_a = Mock()
    mock_b = Mock()
    mock_c = Mock()
    t.events.a.connect(mock_a)
    t.events.b.connect(mock_b)
    t.events.c.connect(mock_c)

    # setting t.c emits events for all three a, b, and c
    t.c = [10, 20]
    mock_a.assert_called_with(10)
    mock_b.assert_called_with(20)
    mock_c.assert_called_with([10, 20])
    assert t.a == 10
    assert t.b == 20

    mock_a.reset_mock()
    mock_b.reset_mock()
    mock_c.reset_mock()

    # setting t.a emits events for a and c, but not b
    # this is because we declared c to be dependent on ['a', 'b']
    t.a = 5
    mock_a.assert_called_with(5)
    mock_c.assert_called_with([5, 20])
    mock_b.assert_not_called()
    assert t.c == [5, 20]
