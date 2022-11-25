from mypyc.build import mypycify
from setuptools import setup

COMPILED = ["src/psygnal/_signal.py", "src/psygnal/_group.py"]
setup(
    ext_modules=mypycify(COMPILED),
    package_dir={"": "src"},  # needed for CI
    # these two are defined in pyproject.toml
    # but added here for the sake of github:
    # See: https://github.com/github/feedback/discussions/6456
    name="psygnal",
    install_requires=[
        "typing-extensions",
        "importlib_metadata ; python_version < '3.8'",
    ],
)
