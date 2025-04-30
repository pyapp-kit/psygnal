# Evented Containers

These classes provide "evented" versions of mutable python containers.
They each have an `events` attribute (`SignalGroup`) that has a variety of
signals that will emit whenever the container is mutated.  See
[Container SignalGroups](#container-signalgroups) for the corresponding
container type for details on the available signals.

## Container SignalGroups
