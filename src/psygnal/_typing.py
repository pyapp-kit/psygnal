"""`TypeVarTuple` and `Unpack` for every supported Python version."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any, TypeVar

if sys.version_info >= (3, 11):
    from typing import TypeVarTuple as TypeVarTuple
    from typing import Unpack as Unpack
elif TYPE_CHECKING:
    from typing_extensions import TypeVarTuple as TypeVarTuple
    from typing_extensions import Unpack as Unpack
else:
    try:
        from typing_extensions import TypeVarTuple, Unpack
    except ImportError:

        class _UnpackFallback:
            def __getitem__(self, item: Any) -> Any:
                return item

        # typing has neither name before Python 3.11. Without typing_extensions
        # a class generic over a `TypeVarTuple` takes a single type argument at
        # runtime: `Signal[int]` works and `Signal[int, str]` raises TypeError.
        # Type checkers are not affected.
        TypeVarTuple = TypeVar
        Unpack = _UnpackFallback()
