import subprocess
from pathlib import Path

from PyInstaller import __main__ as pyi_main


def test_pyintstaller_hiddenimports(tmp_path: Path) -> None:
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
    pyi_main.run(args)
    subprocess.run([str(dist_path / app_name / app_name)], check=True)
