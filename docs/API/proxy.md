# Proxy Objects

These objects provide "evented" subclasses of
[`wrapt.ObjectProxy`](https://wrapt.readthedocs.io/en/latest/wrappers.html#object-proxy)
They are intended to provide signals whenever the wrapped object is modified,
for example, by setting/deleting an attribute, by getting/deleting an item, or
by calling the wrapped object if it is callable.

!!! warning

    These objects are experimental! They may affect the behavior of
    the wrapped object in unanticipated ways.  Please consult
    the [wrapt documentation](https://wrapt.readthedocs.io/en/latest/wrappers.html)
    for details on how the Object Proxy works.

::: psygnal.containers.EventedObjectProxy
::: psygnal.containers.EventedCallableObjectProxy
