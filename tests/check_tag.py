#!/usr/bin/env python3
import os
import re
import sys

from psygnal import __version__


def _main(env_var: str = "GITHUB_REF") -> int:
    git_ref = os.getenv(env_var, "none")
    tag = re.sub("^refs/tags/v*", "", git_ref.lower())
    version = __version__.lower()
    if tag == version:
        print(
            f"✓ {env_var} env var {git_ref!r} matches package version: "
            f"{tag!r} == {version!r}"
        )
        return 0
    else:
        print(
            f"✖ {env_var} env var {git_ref!r} does not match package version: "
            f"{tag!r} != {version!r}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(_main())
