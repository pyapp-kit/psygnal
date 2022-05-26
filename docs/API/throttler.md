# Throttling & Debouncing

[Throttling and
debouncing](https://stackoverflow.com/questions/25991367/difference-between-throttling-and-debouncing-a-function)
are techniques used to prevent a frequently-emitted signal from triggering a
specific callback more than some amount in a specified amount of time.

*Throttling* means preventing a callback from being called if it has recently been
called; it is useful when the callback is expensive.

*Debouncing* means waiting
for a period of time to pass *before* calling the callback; it is useful when
you'd like to wait a moment to see if a user might do additional actions (say,
moving a slider or typing in a text field) before "comitting" to calling the
callback.

::: psygnal.throttled
::: psygnal.debounced
