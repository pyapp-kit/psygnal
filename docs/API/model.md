# Evented Model

This class provides an "evented" version of pydantic's
[`BaseModel`](https://pydantic-docs.helpmanual.io/usage/models/),
that emits a signal whenever a field value is changed

This is an alternative to using the lighter-weight
[`@evented` dataclass decorator](../dataclasses.md). In addition to
simply gaining events on all fields, the `EventedModel` provides additional
features including `property.setters`, and json encoding features.  See below.

::: psygnal.EventedModel
