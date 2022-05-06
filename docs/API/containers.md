# Evented Containers

These classes provide "evented" versions of mutable python containers.
They each have an `events` attribute (`SignalGroup`) that has a variety of
signals that will emit whenever the container is mutated.  See
[Container SignalGroups](#container-signalgroups) for the corresponding
container type for details on the available signals.

::: psygnal.containers.EventedDict
::: psygnal.containers.EventedList
::: psygnal.containers.EventedSet
::: psygnal.containers.EventedOrderedSet
::: psygnal.containers.Selection
::: psygnal.containers.SelectableEventedList

## Container SignalGroups

::: psygnal.containers._evented_dict.DictEvents
    rendering:
      show_source: false
      heading_level: 3
::: psygnal.containers._evented_list.ListEvents
    selection:
      members: []
    rendering:
      show_source: false
      heading_level: 3
::: psygnal.containers._evented_set.SetEvents
    rendering:
      show_source: false
      heading_level: 3
::: psygnal.containers._selection.SelectionEvents
    rendering:
      show_source: false
      heading_level: 3
