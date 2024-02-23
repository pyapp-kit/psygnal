from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType

    import pydantic.version

    if pydantic.version.VERSION.startswith("2"):
        from ._evented_model_v2 import EventedModel as EventedModelv1
    else:
        from ._evented_model_v1 import EventedModel as EventedModelv2


class ComparisonDelayer:
    def __init__(self, target: EventedModelv1 | EventedModelv2) -> None:
        self._target = target

    def __enter__(self) -> None:
        self._target._delay_check_semaphore += 1

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._target._delay_check_semaphore -= 1
        self._target._check_if_values_changed_and_emit_if_needed()
