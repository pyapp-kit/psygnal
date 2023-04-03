class EmitLoopError(Exception):
    """Error type raised when an exception occurs during a callback."""

    def __init__(self, slot_repr: str, args: tuple, exc: BaseException) -> None:
        self.slot_repr = slot_repr
        self.args = args
        self.__cause__ = exc  # mypyc doesn't set this, but uncompiled code would
        super().__init__(
            f"calling {self.slot_repr} with args={args!r} caused "
            f"{type(exc).__name__}: {exc}."
        )
