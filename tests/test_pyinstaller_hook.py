import importlib.util
import os
import subprocess
import warnings
from pathlib import Path

import pytest

import psygnal


@pytest.mark.skipif(not psygnal._compiled, reason="Compiled psygnal not found")
def test_hook_content():
    spec = importlib.util.spec_from_file_location(
        "hook",
        os.path.join(
            os.path.dirname(psygnal.__file__), "_pyinstaller_util", "hook-psygnal.py"
        ),
    )
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)

    assert "psygnal._dataclass_utils" in hook.hiddenimports


def test_pyintstaller_hiddenimports(tmp_path: Path) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        from PyInstaller import __main__ as pyi_main

    build_path = tmp_path / "build"
    dist_path = tmp_path / "dist"
    app_name = "psygnal_test"
    app = tmp_path / (app_name + ".py")
    app.write_text("\n".join(["import psygnal", "print(psygnal.__version__)"]))

    args = [
        # Place all generated files in ``tmp_path``.
        "--workpath",
        str(build_path),
        "--distpath",
        str(dist_path),
        "--specpath",
        str(tmp_path),
        str(app),
    ]

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # silence warnings about deprecations
        pyi_main.run(args)
    subprocess.run([str(dist_path / app_name / app_name)], check=True)
