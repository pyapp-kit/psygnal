# Evented Dataclasses

A common usage of signals in an application is to notify other parts of the
application when a particular object or value has changed. More often than not,
these values are attributes on some object.  Dataclasses are a very common way
to represent such objects, and `psygnal` provides a convenient way to add the
observer pattern to any dataclass.

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

There are multiple hird-party libraries that also implement this pattern, or
something similar:

- [pydantic](https://pydantic-docs.helpmanual.io/) provides a
  [`BaseModel` class](https://pydantic-docs.helpmanual.io/usage/models/),
  a dataclass-like object that can additionally perform type validation and facilitates
  serialization to and from JSON.
- [msgspec](https://jcristharif.com/msgspec/) provides a
  [`Struct` class](https://jcristharif.com/msgspec/structs.html) that is extremely
  fast and lightweight, with an emphasis on serialization.
- the [`attrs` library](https://www.attrs.org/en/stable/) provides [the `@define`
  decorator](https://www.attrs.org/en/stable/overview.html), which is similar to
  the `@dataclass` decorator, but with a few additional features.

All of these libraries are still in common use, and each has its own
strengths and weaknesses (discussed in depth elsewhere).

## The observer pattern

The [observer pattern](https://en.wikipedia.org/wiki/Observer_pattern) is a software design pattern in which an object, named the **subject**, maintains a list of its dependents, called **observers**, and notifies them automatically of any state changes, usually by calling a **callback function** provided by the observer.

**psygnal implements the observer pattern.**

Here is a simple example of a class that uses `psygnal` to notify
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

# create an instance of the class
john = Person()

# now we can connect a callback to the `age_changed` signal
def my_callback(age: int):
    print(f"John's age changed to {age}.")

john.age_changed.connect(my_callback)
```

But there's a lot of boilerplate here.  We have to define a signal and
create a setter method that emits that signal (for each field!).
This is where `psygnal`'s dataclass support comes in handy.

## Adding the observer pattern to any dataclass using Psygnal

`psygnal` provides the ability to make a dataclass "evented", meaning that
any time a field value is changed, a signal will be emitted. psygnal's
[`SignalGroupDescriptor`][psygnal.SignalGroupDescriptor] does this by:

1. Inspecting the object to determine what the (mutable) fields are (psygnal has
awareness of multiple dataclass libraries, including the standard library's
`dataclasses` module)
2. Creating a [`SignalGroup`][psygnal.SignalGroup] with a
   [`SignalInstance`][psygnal.SignalInstance] for each field name
3. Adding the `SignalGroup` as a new attribute on the object

A signal will be then emitted whenever the field value is changed,
with the new value as the first argument.

There are two (related) APIs for adding events to dataclasses:

1. Add a [`SignalGroupDescriptor`][psygnal.SignalGroupDescriptor] as a class attribute.

    !!! example

        === "dataclasses"

            ```python
            from typing import ClassVar
            from psygnal import SignalGroupDescriptor
            from dataclasses import dataclass

            @dataclass
            class Person:
                name: str
                age: int = 0
                events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor()
            ```

        === "pydantic"

            ```python
            from typing import ClassVar
            from psygnal import SignalGroupDescriptor
            from pydantic import BaseModel

            class Person(BaseModel):
                name: str
                age: int = 0
                events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor()
            ```

            *for a fully evented subclass of pydantic's `BaseModel`, see also
            [`EventedModel`](./API/model.md)*

        === "msgspec"

            ```python
            from typing import ClassVar
            from psygnal import SignalGroupDescriptor
            import msgspec

            class Person(msgspec.Struct):
                name: str
                age: int = 0
                events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor()

            # haven't yet figured out a more elegant way to do this
            from psygnal._group_descriptor import evented_setattr
            Foo.__setattr__ = evented_setattr(Foo, "events")
            ```

            !!!warning
                As you can see, using the descriptor with `msgspec` still requires using a private API.  If you find this API useful and would like to see it public, please
                [open an issue](https://github.com/pyapp-kit/psygnal/issues/new)

        === "attrs"

            ```python
            from typing import ClassVar
            from psygnal import SignalGroupDescriptor
            from attrs import define

            @define
            class Person:
                name: str
                age: int = 0
                events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor()
            ```

2. Decorate the class with the [`@evented` decorator][psygnal.evented].

    > *Under the hood, this just adds the `SignalGroupDescriptor` as a class
    > attribute named "events" for you, as shown above). Prefer the class
    > attribute pattern to the decorator when in doubt.*

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

        === "msgspec"

            ```python
            from psygnal import evented
            import msgspec

            @evented
            class Person(msgspec.Struct):
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

    !!! tip
        by default, the `SignalGroup` instance is named `'events'`, but this can be
        changed by passing a `events_namespace` argument to the `@evented` decorator)

Using any of the above, you can now connect callbacks to the change events
of any field on the object (there will be a signal instance in the `events`
attribute for each mutable field in your dataclass)

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

You can also connect to the `SignalGroup` itself to listen to *any*
changes on the obect:

```python
from psygnal import EmissionInfo

@john.events.connect
def on_any_change(info: EmissionInfo):
    print(f"field {info.signal.name!r} changed to {info.args}")
```

see the [API documentation](./API/evented.md) for for more details.

## Type annotating evented dataclasses

If you use the `SignalGroupDescriptor` API, it is easier for type checkers
because you are explicitly providing the `events` namespace for the SignalGroup.

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
