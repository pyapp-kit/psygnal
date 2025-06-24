# Evented Dataclasses

A common usage of signals in an application is to notify other parts of the
application when a particular object or value has changed. More often than not,
these values are attributes on some object. Dataclasses are a very common way
to represent such objects, and `psygnal` provides a convenient way to add the
observer pattern to any dataclass.

## What is a dataclass

A "data class" is a class that is primarily used to store a set of data. Of
course, _most_ python data structures (e.g. `tuples`, `dicts`) are used to store
a set of data, but when we refer to a "data class" we are generally referring to
a class that formally defines a set of fields or attributes, each with a name,
a current value, and (preferably) a type. The values could represent anything,
such as a configuration of some sort, a set of parameters, or a set of data
that is being processed.

### ... in the standard library

Python 3.7 introduced [the `dataclasses`
module](https://docs.python.org/3/library/dataclasses.html), which provides a
decorator that can be used to easily create such classes with a minimal amount
of boilerplate. For example:

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

There are multiple third-party libraries that also implement this pattern, or
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

But there's a lot of boilerplate here. We have to define a signal and
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

### 1. Use `SignalGroupDescriptor`

[`SignalGroupDescriptor`][psygnal.SignalGroupDescriptor] is designed to be used
as a class attribute on a dataclass-like object, and, when accessed on an
instance of that class, will return a [`SignalGroup`][psygnal.SignalGroup] with
signals for each field in the class.

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
        [`EventedModel`](./model.md)*

    === "msgspec"

        ```python
        from typing import ClassVar
        from psygnal import SignalGroupDescriptor
        import msgspec

        class Person(msgspec.Struct):
            name: str
            age: int = 0
            events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor()
        ```

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

### 2. Use the `@evented` decorator

The [`@evented`][psygnal.evented] decorator can be added to any dataclass-like
class. Under the hood, this just adds the `SignalGroupDescriptor` as a class
attribute for you (named "events" by default), as shown above. Prefer the class
attribute pattern (`events = SignalGroupDescriptor()`) to the decorator when
in doubt, as it is more explicit and leads to better type checking.

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
        [`EventedModel`](./model.md)*

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

You can also connect to the `SignalGroup` itself to listen to _any_
changes on the object:

```python
from psygnal import EmissionInfo

@john.events.connect
def on_any_change(info: EmissionInfo):
    print(f"field {info.signal.name!r} changed to {info.args}")
```

see the [API documentation](reference/psygnal/) for for more details.

## Type annotating evented dataclasses

If you use the `SignalGroupDescriptor` API, it is easier for type checkers
because you are explicitly providing the `events` namespace for the SignalGroup.

By default, type checkers and IDEs will not know about the signals that are
dynamically added to the class by the `@evented` decorator. If you'd like
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

## Event Bubbling

When you have nested evented objects (dataclasses containing other dataclasses,
or evented containers), **event bubbling** allows you to automatically
receive events from child objects. This creates a hierarchical event system
where changes deep in the object tree bubble up to parent listeners.

### Enabling Event Bubbling

Event bubbling is enabled **by default**, but to be explicit, or to disable it,
you can set the `connect_child_events` parameter when creating your
[`SignalGroupDescriptor`][psygnal.SignalGroupDescriptor],
or when using the [`@evented`][psygnal.evented] decorator.

=== "evented decorator"

    ```python
    from dataclasses import dataclass, field
    from typing import ClassVar

    from psygnal import SignalGroupDescriptor, evented

    @evented(connect_child_events=True)  # default is True
    @dataclass 
    class Person:
        name: str = ""
        age: int = 0

    @evented(connect_child_events=True)  # default is True
    @dataclass
    class Team:
        name: str = ""
        leader: Person = field(default_factory=Person)
        
    team = Team()

    # Listen for ANY event from the team or its children
    team.events.connect(lambda info: print(f"Event: {info}"))

    # This will trigger the listener above
    team.leader.name = "Alice"
    ```

=== "SignalGroupDescriptor"

    ```python
    from dataclasses import dataclass, field
    from typing import ClassVar

    from psygnal import SignalGroupDescriptor, evented

    @dataclass 
    class Person:
        name: str = ""
        age: int = 0

        events: ClassVar = SignalGroupDescriptor(
            connect_child_events=True  # default is True
        )

    @dataclass
    class Team:
        name: str = ""
        leader: Person = field(default_factory=Person)
        
        events: ClassVar = SignalGroupDescriptor(
            connect_child_events=True  # default is True
        )

    team = Team()

    # Listen for ANY event from the team or its children
    team.events.connect(lambda info: print(f"Event: {info}"))

    # This will trigger the listener above
    team.leader.name = "Alice"
    ```

### Understanding Event Paths

Events bubble up via [`SignalGroups`][psygnal.SignalGroup].  And, as a reminder,
when you connect to a `SignalGroup`, the callback receives an
[`EmissionInfo`][psygnal.EmissionInfo] object that contains information about the
event, including the signal that was emitted, and the arguments passed to it.

It _also_ includes a **path** that tracks where the event originated,
The path is a tuple of [`psygnal.PathStep`][] objects showing the route from the
parent to the child that emitted the event:

```python
from psygnal import EmissionInfo


@dataclass
class Department:
    events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor(
        connect_child_events=True
    )
    name: str = ""
    team: Team = field(default_factory=lambda: Team())

dept = Department()

def show_event_path(info: EmissionInfo):
    print(f"Changed: {info.signal}")
    print(f"Args: {info.args}")
    print(f"Path: {''.join(str(step) for step in info.path)}")

dept.events.connect(show_event_path)

# Change a deeply nested value
dept.team.leader.age = 30

# Output:
# Changed: <SignalInstance 'age' at 0x...>
# Args: (30, 0)
# Path: .team.leader.age
```

### Working with Evented Containers

Event bubbling also works with evented containers like `EventedList`:

```python
from psygnal.containers import EventedList

@dataclass
class Project:
    name: str = ""
    team_members: EventedList = field(default_factory=EventedList)

    # (the explicit way to make this an evented dataclass)
    events: ClassVar[SignalGroupDescriptor] = SignalGroupDescriptor(
        connect_child_events=True
    )

project = Project()
project.events.connect(lambda info: print(f"{info.signal.name}: {info.args} {info.path}"))

# Add a person to the list - EventedList emits two events here:
project.team_members.append(Person(name="Bob"))
# inserting: (0,) (.team_members, [0])
# inserted: (0, Person(name='Bob', age=0)) (.team_members, [0])

# Change a person in the list - this also bubbles up
project.team_members[0].age = 25
# age: (25, 0) (.team_members, [0], .age)
```

### Common Use Cases

Event bubbling is particularly useful for:

- **Reactive UIs**: Automatically update displays when any part of a complex
  or nested data model changes
- **Change tracking**: Log or persist changes anywhere in a nested object
  hierarchy  
- **Undo/redo systems**: Track all changes in a complex object tree

!!! tip
    Event bubbling adds minimal overhead but can generate many events in deeply
    nested structures. Consider using [throttling](throttler.md) for
    high-frequency updates or connect to specific signals when you don't need
    all events.

## Performance cost of evented dataclasses

Adding signal emission on every field change is definitely not without cost, as
it requires 2 additional `getattr` calls and an equality check for every field
change.

The scale of the penalty will depend on the flavor of dataclass you are using,
with fast dataclasses like `msgspec` taking a much bigger hit than slower ones.

The following table shows the minimum time it took (on my computer) to set an
attribute on a dataclass, with and without signal emission. (Timed using `timeit`,
with 20 repeats of 100,000 iterations each).

| dataclass     | without signals | with signals | penalty (fold slower) |
| ------------- | --------------- | ------------ | --------------------- |
| `pydantic v1` | 0.386 µs        | 0.902 µs     | 2.33                  |
| `pydantic v2` | 1.533 µs        | 2.145 µs     | 1.39                  |
| `dataclasses` | 0.015 µs        | 0.371 µs     | 24.55                 |
| `msgspec`     | 0.026 µs        | 0.561 µs     | 21.85                 |
| `attrs`       | 0.014 µs        | 0.540 µs     | 37.85                 |
