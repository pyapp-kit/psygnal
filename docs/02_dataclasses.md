# Evented Dataclasses

A common usage of signals in an application is to notify other
parts of the application when a particular object or value has changed.
More often than not, these values are attributes on some object:

Here is a simple example of a class that uses signals to notify
other parts of the application when its `age` attribute changes:

```python
from psygnal import Signal

class Person:
    age_changed: Signal(int)

    @property
    def age(self):
        return self._age

    @age.setter
    def age(self, value):
        self._age = value
        self.age_changed(value)
```

## What is a dataclass

A "data class" is a class that is primarily used to store a set of data. Of
course, *most* python data structures (e.g. `tuples`, `dicts`) are used to store
a set of data, but when we refer to a "data class" we are generally referring to
a class that formally defines a set of fields or attributes, each with a name,
a current value, and (preferably) a type.  The values could represent anything,
such as a configuration of some sort, a set of parameters, or a set of data
that is being processed.

### ... in the standard library

Python 3.7 introduced [the `dataclasses`
module](https://docs.python.org/3/library/dataclasses.html), which provides a
decorator that can be used to easily create such classes with a minimal amount
of boilerplate.  For example:

```python
from dataclasses import dataclass

@dataclass
class Person:
    name: str
    age: int = 0

john = Person(name="John", age=30)
print(john)  # prints: Person(name='John', age=30)
```

!!! hint
    There's a lot more to be learned about dataclasses! See the [python
    docs](https://docs.python.org/3/library/dataclasses.html) for more, and
    [this realpython blog post](https://realpython.com/python-data-classes/) for
    an in-depth introduction.

### ... in third-party libraries

Prior to the addition of dataclasses in the standard library, third-party libraries
were already implementing this pattern:

- the [`attrs` library](https://www.attrs.org/en/stable/) provides [the `@define`
  decorator](https://www.attrs.org/en/stable/overview.html), which is similar to
  the `@dataclass` decorator, but with a few additional features.
- [pydantic](https://pydantic-docs.helpmanual.io/) provides a
  [`BaseModel` class](https://pydantic-docs.helpmanual.io/usage/models/),
  a dataclass-like object that can additionally perform type validation and facilitates
  serialization to and from JSON.

All of these libraries are still in common use, and each has its own
strengths and weaknesses (discussed in depth elsewhere).

## Evented dataclasses in Psygnal

`psygnal` provides an [`@evented` decorator][psygnal.evented] that can be used
to decorate any existing dataclass (standard library, `attrs`, or `pydantic`
model). It adds a new [`SignalGroup`][psygnal.SignalGroup] property to the
class, with a [`SignalInstance`][psygnal.SignalInstance] for each field in the
dataclass.  A Signal will be emitted whenever the field value is changed, with
the new value as the first argument.

!!! example

    === "dataclasses"

        ```python
        from psygnal import evented
        from dataclasses import dataclass

        @evented
        @dataclass
        class Person:
            name: str
            age: int = 0
        ```

    === "attrs"

        ```python
        from psygnal import evented
        from attrs import define

        @evented
        @define
        class Person:
            name: str
            age: int = 0
        ```

    === "pydantic"

        ```python
        from psygnal import evented
        from pydantic import BaseModel

        @evented
        class Person(BaseModel):
            name: str
            age: int = 0
        ```

        *for a fully evented subclass of pydantic's `BaseModel`, see also
        [`EventedModel`](./API/model.md)*

using any of the above, you can now do:

```python
# create an instance of the dataclass
john = Person(name="John", age=30)

# now we can connect a callback to any event on the `events` namespace
@john.events.age.connect
def on_age_changed(age: int):
    print(f"John's age changed to {age}.")

# change a value
john.age = 31  # prints: John's age changed to 31.
```

!!! tip
    by default, the `SignalGroup` instance is named `'events'`, but this can be
    changed by passing a `events_namespace` argument to the `@evented` decorator)

see the API documentation for [`@evented`][psygnal.evented] for more details.

## Type annotating evented dataclasses

By default, type checkers and IDEs will not know about the signals that are
dynamically added to the class by the `@evented` decorator.  If you'd like
to have your type checker or IDE know about the signals, you can add an
annotation as follows:

```python
from psygnal import evented
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psygnal import SignalGroup

    class PersonSignalGroup(SignalGroup):
        name: SignalInstance
        age: SignalInstance


@evented
@dataclass
class Person:
    # just one of a few ways to annotate the `events` namespace
    if TYPE_CHECKING:
        events: PersonSignalGroup

    name: str
    age: int = 0
```

!!! note
    I know... it's not awesome :/

    Remember that adding these type annotations is optional: signals
    will still work without them.  But your IDE will not know that Person
    has an `events` attribute, and it will not know that `events.name` is
    a `SignalInstance`.

    If you have any ideas for how to improve this, please let me know!
