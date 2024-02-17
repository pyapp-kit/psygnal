__all__ = ["mypyc_attr"]

try:
    # mypy_extensions is not required at runtime, it's only used by mypyc
    # to provide type information to the mypyc compiler.
    # we include it in the [tool.hatch.build.targets.wheel.hooks.mypyc]
    # section of pyproject.toml so that it's available when building.
    from mypy_extensions import mypyc_attr
except ImportError:

    def mypyc_attr(*_, **__):  # type: ignore
        return lambda x: x
