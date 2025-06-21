# Evented Model

This class provides an "evented" version of pydantic's
[`BaseModel`](https://pydantic-docs.helpmanual.io/usage/models/), that emits a
signal whenever a field value is changed

This is an alternative to using the lighter-weight [`@evented` dataclass
decorator](./dataclasses.md). In addition to simply gaining events on all
fields, the [`EventedModel`][psygnal.EventedModel] provides additional features including
`property.setters`, and json encoding features.

```python
from psygnal import EventedModel

class MyModel(EventedModel):
    x: int = 1
    y: int = 2

# Create an instance of the model
model = MyModel()

# Connect to the `x` field's event
model.events.x.connect(lambda value: print(f"x changed to {value}"))

# Update the `x` field
model.x = 42  # Prints: "x changed to 42"
```

In this example:

- The `EventedModel` automatically creates events for each field.
- You can connect callbacks to these events to respond to changes in field
  values.

See documentation for the [`EventedModel`][psygnal.EventedModel] class for
more.