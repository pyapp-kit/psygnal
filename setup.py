import os
import sys

import setuptools

ext_modules = None
if (
    all(arg not in sys.argv for arg in ["clean", "check"])
    and "SKIP_CYTHON" not in os.environ
):
    try:
        from Cython.Build import cythonize
    except ImportError:
        pass
    else:
        # For cython test coverage install with `make build-trace`
        compiler_directives = {}
        if "CYTHON_TRACE" in sys.argv:
            compiler_directives["linetrace"] = True
        # Set CFLAG to all optimizations (-O3)
        # Any additional CFLAGS will be appended.
        # Only the last optimization flag will have effect
        os.environ["CFLAGS"] = "-O3 " + os.environ.get("CFLAGS", "")
        ext_modules = cythonize(
            "psygnal/*.py",
            nthreads=int(os.getenv("CYTHON_NTHREADS", 0)),
            language_level=3,
            compiler_directives=compiler_directives,
        )

setuptools.setup(
    use_scm_version={"write_to": "psygnal/_version.py"},
    ext_modules=ext_modules,
)
