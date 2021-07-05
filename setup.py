import os
import sys
from distutils.command import build_ext

import setuptools

if os.name == "nt":

    # fix LINK : error LNK2001: unresolved external symbol PyInit___init__
    # Patch from: https://bugs.python.org/issue35893

    def get_export_symbols(self, ext):  # type: ignore
        """
        Slightly modified from:
        https://github.com/python/cpython/blob/8849e5962ba481d5d414b3467a256aba2134b4da\
        /Lib/distutils/command/build_ext.py#L686-L703
        """
        parts = ext.name.split(".")
        suffix = parts[-2] if parts[-1] == "__init__" else parts[-1]
        # from here on unchanged
        try:
            # Unicode module name support as defined in PEP-489
            # https://www.python.org/dev/peps/pep-0489/#export-hook-name
            suffix.encode("ascii")
        except UnicodeEncodeError:
            suffix = "U" + suffix.encode("punycode").replace(b"-", b"_").decode("ascii")

        initfunc_name = "PyInit_" + suffix
        if initfunc_name not in ext.export_symbols:
            ext.export_symbols.append(initfunc_name)
        return ext.export_symbols

    build_ext.build_ext.get_export_symbols = get_export_symbols  # type: ignore


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
