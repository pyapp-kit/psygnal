from typing import Any, get_origin

import pytest

try:
    import pydantic
except ImportError:
    pytest.skip("pydantic not installed", allow_module_level=True)

from psygnal import containers

V1 = pydantic.__version__.startswith("1")


@pytest.mark.skipif(V1, reason="pydantic v1 has poor support for generics")
@pytest.mark.parametrize(
    "hint",
    [
        containers.EventedList[int],
        containers.SelectableEventedList[int],
    ],
)
def test_evented_list_as_pydantic_field(hint: Any) -> None:
    class Model(pydantic.BaseModel):
        my_list: hint

    m = Model(my_list=[1, 2, 3])  # type: ignore
    assert m.my_list == [1, 2, 3]
    assert isinstance(m.my_list, get_origin(hint))

    m2 = Model(my_list=containers.EventedList([1, 2, 3]))
    assert m2.my_list == [1, 2, 3]
    m3 = Model(my_list=[1, "2", 3])  # type: ignore
    assert m3.my_list == [1, 2, 3]
    assert isinstance(m3.my_list, get_origin(hint))

    with pytest.raises(pydantic.ValidationError):
        Model(my_list=[1, 2, "string"])  # type: ignore


@pytest.mark.skipif(V1, reason="pydantic v1 has poor support for generics")
def test_evented_list_no_params_as_pydantic_field() -> None:
    class Model(pydantic.BaseModel):
        my_list: containers.EventedList

    m = Model(my_list=[1, 2, 3])  # type: ignore
    assert m.my_list == [1, 2, 3]
    assert isinstance(m.my_list, containers.EventedList)

    m3 = Model(my_list=[1, "string", 3])  # type: ignore
    assert m3.my_list == [1, "string", 3]
    assert isinstance(m3.my_list, containers.EventedList)


@pytest.mark.skipif(V1, reason="pydantic v1 has poor support for generics")
@pytest.mark.parametrize(
    "hint",
    [
        containers.EventedSet[str],
        containers.EventedOrderedSet[str],
        containers.Selection[str],
    ],
)
def test_evented_set_as_pydantic_field(hint: Any) -> None:
    class Model(pydantic.BaseModel):
        my_set: hint

        model_config = {"coerce_numbers_to_str": True}

    m = Model(my_set=[1, 2])  # type: ignore
    assert m.my_set == {"1", "2"}  # type: ignore
    assert isinstance(m.my_set, get_origin(hint))

    m2 = Model(my_set=containers.EventedSet(["a", "b"]))
    assert m2.my_set == {"a", "b"}  # type: ignore
    m3 = Model(my_set=[1, "2", 3])  # type: ignore
    assert m3.my_set == {"1", "2", "3"}  # type: ignore
    assert isinstance(m3.my_set, get_origin(hint))


@pytest.mark.skipif(V1, reason="pydantic v1 has poor support for generics")
def test_evented_dict_as_pydantic_field() -> None:
    class Model(pydantic.BaseModel):
        my_dict: containers.EventedDict[str, int]

        model_config = {"coerce_numbers_to_str": True}

    m = Model(my_dict={"a": 1})  # type: ignore
    assert m.my_dict == {"a": 1}
    assert isinstance(m.my_dict, containers.EventedDict)

    m2 = Model(my_dict=containers.EventedDict({"a": 1}))
    assert m2.my_dict == {"a": 1}
    assert isinstance(m2.my_dict, containers.EventedDict)

    m3 = Model(my_dict={1: "2"})  # type: ignore
    assert m3.my_dict == {"1": 2}
    assert isinstance(m3.my_dict, containers.EventedDict)

    with pytest.raises(pydantic.ValidationError):
        Model(my_dict={"a": "string"})  # type: ignore
