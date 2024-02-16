import inspect
import sys
from typing import Any, ClassVar, List, Sequence, Union
from unittest.mock import Mock, call, patch

import numpy as np
import pytest
from typing_extensions import Protocol, runtime_checkable

try:
    from pydantic import PrivateAttr
except ImportError:
    pytest.skip("pydantic not installed", allow_module_level=True)

import pydantic.version
from pydantic import BaseModel

from psygnal import EmissionInfo, EventedModel
from psygnal._group import SignalGroup

PYDANTIC_V2 = pydantic.version.VERSION.startswith("2")

try:
    from pydantic import field_serializer
except ImportError:

    def field_serializer(*args, **kwargs):
        def decorator(cls):
            return cls

        return decorator


def asdict(obj: "BaseModel") -> dict:
    if PYDANTIC_V2:
        return obj.model_dump()
    else:
        return obj.dict()


def asjson(obj: BaseModel) -> str:
    if PYDANTIC_V2:
        return obj.model_dump_json()
    else:
        return obj.json()


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
    with pytest.warns(FutureWarning):
        assert "id" in user.events.signals
        assert "name" in user.events.signals

    # ClassVars are excluded from events
    assert "age" not in user.events

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


def test_evented_model_array_updates():
    """Test updating an evented pydantic model with an array."""

    class Model(EventedModel):
        """Demo evented model."""

        values: np.ndarray

        if PYDANTIC_V2:
            model_config = {"arbitrary_types_allowed": True}
        else:

            class Config:
                arbitrary_types_allowed = True

    first_values = np.array([1, 2, 3])
    model = Model(values=first_values)

    # Mock events
    values_mock = Mock()
    model.events.values.connect(values_mock)

    np.testing.assert_almost_equal(model.values, first_values)

    # Updating with new data
    new_array = np.array([1, 2, 4])
    model.values = new_array
    np.testing.assert_array_equal(values_mock.call_args.args[0], new_array)
    values_mock.reset_mock()

    # Updating with same data, no event should be emitted
    model.values = new_array
    values_mock.assert_not_called()


def test_evented_model_np_array_equality():
    """Test checking equality with an evented model with direct numpy."""

    class Model(EventedModel):
        values: np.ndarray

        if PYDANTIC_V2:
            model_config = {"arbitrary_types_allowed": True}
        else:

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

        if PYDANTIC_V2:
            model_config = {"arbitrary_types_allowed": True}
        else:

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


def test_values_updated() -> None:
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
        user_name: str = "A"
        age: ClassVar[int] = 100

    user1 = User(id=0)
    user2 = User(id=1, user_name="K")
    # Check user1 and user2 dicts
    assert asdict(user1) == {"id": 0, "user_name": "A"}
    assert asdict(user2) == {"id": 1, "user_name": "K"}

    # Add mocks
    user1_events = Mock()
    u1_id_events = Mock()
    u2_id_events = Mock()

    user1.events.all.connect(user1_events)
    user1.events.all.connect(user1_events)

    user1.events.id.connect(u1_id_events)
    user2.events.id.connect(u2_id_events)
    user1.events.id.connect(u1_id_events)
    user2.events.id.connect(u2_id_events)

    # Update user1 from user2
    user1.update(user2)
    assert asdict(user1) == {"id": 1, "user_name": "K"}

    u1_id_events.assert_called_with(1)
    u2_id_events.assert_not_called()

    # NOTE:
    # user.events.user_name is NOT actually emitted because it has no callbacks
    # connected to it.  see test_comparison_count below...
    user1_events.assert_has_calls(
        [
            call(EmissionInfo(signal=user1.events.id, args=(1,))),
            # call(EmissionInfo(signal=user1.events.user_name, args=("K",))),
        ]
    )
    u1_id_events.reset_mock()
    u2_id_events.reset_mock()
    user1_events.reset_mock()

    # Update user1 from user2 again, no event emission expected
    user1.update(user2)
    assert asdict(user1) == {"id": 1, "user_name": "K"}

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
        def string(self) -> str: ...

        # Protocol fields are not successfully set without explicit validation.
        @classmethod
        def __get_validators__(cls):
            yield cls.validate

        @classmethod
        def __get_pydantic_core_schema__(cls, _source_type: Any, _handler: Any):
            from pydantic_core import core_schema

            return core_schema.no_info_plain_validator_function(cls.validate)

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
        z: bytes = b"zzz"

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
    def __get_pydantic_core_schema__(cls, _source_type: Any, _handler: Any):
        from pydantic_core import core_schema

        return core_schema.no_info_plain_validator_function(cls.validate_type)

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

        @field_serializer("obj")
        def serialize_dt(self, dt: MyObj) -> dict:
            return dt.__dict__

    m = Model(obj=MyObj(1, "hi"))
    raw = asjson(m)
    if PYDANTIC_V2:
        assert raw == '{"obj":{"a":1,"b":"hi"}}'
        deserialized = Model.model_validate_json(raw)
    else:
        assert raw == '{"obj": {"a": 1, "b": "hi"}}'
        deserialized = Model.parse_raw(raw)
    assert deserialized == m


def test_nested_evented_model_serialization():
    """Test that encoders on nested sub-models can be used by top model."""

    class NestedModel(EventedModel):
        obj: MyObj

        @field_serializer("obj")
        def serialize_dt(self, dt: MyObj) -> dict:
            return dt.__dict__

    class Model(EventedModel):
        nest: NestedModel

    m = Model(nest={"obj": {"a": 1, "b": "hi"}})
    raw = asjson(m)
    if PYDANTIC_V2:
        assert raw == r'{"nest":{"obj":{"a":1,"b":"hi"}}}'
        deserialized = Model.model_validate_json(raw)
    else:
        assert raw == r'{"nest": {"obj": {"a": 1, "b": "hi"}}}'
        deserialized = Model.parse_raw(raw)
    assert deserialized == m


def test_evented_model_dask_delayed():
    """Test that evented models work with dask delayed objects"""
    dd = pytest.importorskip("dask.delayed")
    dask = pytest.importorskip("dask")

    class MyObject(EventedModel):
        attribute: dd.Delayed

        if PYDANTIC_V2:
            model_config = {"arbitrary_types_allowed": True}
        else:

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

    if PYDANTIC_V2:
        model_config = {
            "allow_property_setters": True,
            "guess_property_dependencies": True,
        }
    else:

        class Config:
            allow_property_setters = True
            guess_property_dependencies = True


def test_defaults():
    class R(EventedModel):
        x: str = "hi"

    default_r = R()

    class D(EventedModel):
        a: int = 1
        b: int = 1
        r: R = default_r

    d = D()
    assert d._defaults == {"a": 1, "b": 1, "r": default_r}

    d.update({"a": 2, "r": {"x": "asdf"}}, recurse=True)
    assert asdict(d) == {"a": 2, "b": 1, "r": {"x": "asdf"}}
    assert asdict(d) != d._defaults
    d.reset()
    assert asdict(d) == d._defaults


@pytest.mark.skipif(PYDANTIC_V2, reason="enum values seem broken on pydantic")
def test_enums_as_values():
    from enum import Enum

    class MyEnum(Enum):
        A = "value"

    class SomeModel(EventedModel):
        a: MyEnum = MyEnum.A

    m = SomeModel()
    assert asdict(m) == {"a": MyEnum.A}
    with m.enums_as_values():
        assert asdict(m) == {"a": "value"}
    assert asdict(m) == {"a": MyEnum.A}


def test_properties_with_explicit_property_dependencies():
    class MyModel(EventedModel):
        a: int = 1
        b: int = 1

        @property
        def c(self) -> List[int]:
            return [self.a, self.b]

        @c.setter
        def c(self, val: Sequence[int]) -> None:
            self.a, self.b = val

        if PYDANTIC_V2:
            model_config = {
                "allow_property_setters": True,
                "field_dependencies": {"c": ["a", "b"]},
            }
        else:

            class Config:
                allow_property_setters = True
                field_dependencies = {"c": ["a", "b"]}

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
    assert "c" in t.events  # the setter has an event
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


def test_non_setter_with_dependencies() -> None:
    with pytest.raises(
        ValueError, match="Fields with dependencies must be fields or property.setters"
    ):

        class M(EventedModel):
            x: int

            @property
            def y(self): ...

            @y.setter
            def y(self, v): ...

            if PYDANTIC_V2:
                model_config = {
                    "allow_property_setters": True,
                    "field_dependencies": {"a": []},
                }
            else:

                class Config:
                    allow_property_setters = True
                    field_dependencies = {"a": []}


def test_unrecognized_property_dependencies():
    with pytest.warns(UserWarning, match="Unrecognized field dependency: 'b'"):

        class M(EventedModel):
            x: int

            @property
            def y(self): ...

            @y.setter
            def y(self, v): ...

            if PYDANTIC_V2:
                model_config = {
                    "allow_property_setters": True,
                    "field_dependencies": {"y": ["b"]},
                }
            else:

                class Config:
                    allow_property_setters = True
                    field_dependencies = {"y": ["b"]}


@pytest.mark.skipif(PYDANTIC_V2, reason="pydantic 2 does not support this")
def test_setattr_before_init():
    class M(EventedModel):
        _x: int = PrivateAttr()

        def __init__(_model_self_, x: int, **data) -> None:
            _model_self_._x = x
            super().__init__(**data)

        @property
        def x(self) -> int:
            return self._x

    m = M(x=2)
    assert m.x == 2


def test_setter_inheritance():
    class M(EventedModel):
        _x: int = PrivateAttr()

        def __init__(self, x: int, **data: Any) -> None:
            super().__init__(**data)
            self.x = x

        @property
        def x(self) -> int:
            return self._x

        @x.setter
        def x(self, v: int) -> None:
            self._x = v

        if PYDANTIC_V2:
            model_config = {"allow_property_setters": True}
        else:

            class Config:
                allow_property_setters = True

    assert M(x=2).x == 2

    class N(M): ...

    assert N(x=2).x == 2

    with pytest.raises(ValueError, match="Cannot set 'allow_property_setters' to"):

        class Bad(M):
            if PYDANTIC_V2:
                model_config = {"allow_property_setters": False}
            else:

                class Config:
                    allow_property_setters = False


def test_derived_events() -> None:
    class Model(EventedModel):
        a: int

        @property
        def b(self) -> int:
            return self.a + 1

        @b.setter
        def b(self, b: int) -> None:
            self.a = b - 1

        if PYDANTIC_V2:
            model_config = {
                "allow_property_setters": True,
                "field_dependencies": {"b": ["a"]},
            }
        else:

            class Config:
                allow_property_setters = True
                field_dependencies = {"b": ["a"]}

    mock_a = Mock()
    mock_b = Mock()
    m = Model(a=0)
    m.events.a.connect(mock_a)
    m.events.b.connect(mock_b)
    m.b = 3
    mock_a.assert_called_once_with(2)
    mock_b.assert_called_once_with(3)


def test_root_validator_events():
    class Model(EventedModel):
        x: int
        y: int

        if PYDANTIC_V2:
            from pydantic import model_validator

            model_config = {
                "validate_assignment": True,
                "field_dependencies": {"y": ["x"]},
            }

            @model_validator(mode="before")
            def check(cls, values: dict) -> dict:
                x = values["x"]
                values["y"] = min(values["y"], x)
                return values

        else:
            from pydantic import root_validator

            class Config:
                validate_assignment = True
                field_dependencies = {"y": ["x"]}

            @root_validator
            def check(cls, values: dict) -> dict:
                x = values["x"]
                values["y"] = min(values["y"], x)
                return values

    m = Model(x=2, y=1)
    xmock = Mock()
    ymock = Mock()
    m.events.x.connect(xmock)
    m.events.y.connect(ymock)
    m.x = 0
    assert m.y == 0
    xmock.assert_called_once_with(0)
    ymock.assert_called_once_with(0)

    xmock.reset_mock()
    ymock.reset_mock()

    m.x = 2
    assert m.y == 0
    xmock.assert_called_once_with(2)
    ymock.assert_not_called()


def test_deprecation() -> None:
    with pytest.warns(DeprecationWarning, match="Use 'field_dependencies' instead"):

        class MyModel(EventedModel):
            a: int = 1
            b: int = 1

            if PYDANTIC_V2:
                model_config = {"property_dependencies": {"a": ["b"]}}
            else:

                class Config:
                    property_dependencies = {"a": ["b"]}

        assert MyModel.__field_dependents__ == {"b": {"a"}}


def test_comparison_count() -> None:
    """Test that we only compare fields that are actually connected to events."""

    class Model(EventedModel):
        a: int

        @property
        def b(self) -> int:
            return self.a + 1

        @b.setter
        def b(self, b: int) -> None:
            self.a = b - 1

        if PYDANTIC_V2:
            model_config = {
                "allow_property_setters": True,
                "field_dependencies": {"b": ["a"]},
            }
        else:

            class Config:
                allow_property_setters = True
                field_dependencies = {"b": ["a"]}

    # pick whether to mock v1 or v2 modules
    model_module = sys.modules[type(Model).__module__]

    m = Model(a=0)
    b_mock = Mock()
    with patch.object(
        model_module,
        "_check_field_equality",
        wraps=model_module._check_field_equality,
    ) as check_mock:
        m.a = 1

    check_mock.assert_not_called()
    b_mock.assert_not_called()

    m.events.b.connect(b_mock)
    with patch.object(
        model_module,
        "_check_field_equality",
        wraps=model_module._check_field_equality,
    ) as check_mock:
        m.a = 3
    check_mock.assert_has_calls([call(Model, "a", 3, 1), call(Model, "b", 4, 2)])
    b_mock.assert_called_once_with(4)


def test_connect_only_to_events() -> None:
    """Make sure that we still make comparison and emit events when connecting
    only to the events group itself."""

    class Model(EventedModel):
        a: int

    # pick whether to mock v1 or v2 modules
    model_module = sys.modules[type(Model).__module__]

    m = Model(a=0)
    mock1 = Mock()
    with patch.object(
        model_module,
        "_check_field_equality",
        wraps=model_module._check_field_equality,
    ) as check_mock:
        m.a = 1

    check_mock.assert_not_called()
    mock1.assert_not_called()

    m.events.all.connect(mock1)
    with patch.object(
        model_module,
        "_check_field_equality",
        wraps=model_module._check_field_equality,
    ) as check_mock:
        m.a = 3
    check_mock.assert_has_calls([call(Model, "a", 3, 1)])
    mock1.assert_called_once()
