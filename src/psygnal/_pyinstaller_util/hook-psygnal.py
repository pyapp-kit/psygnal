from collections.abc import Iterable
from importlib.metadata import PackageNotFoundError, PackagePath
from importlib.metadata import files as package_files
from pathlib import Path

try:
    import psygnal

    PSYGNAL_DIR = Path(psygnal.__file__).parent
except ImportError:
    PSYGNAL_DIR = Path(__file__).parent.parent


def binary_files(file_list: Iterable[PackagePath | Path]) -> list[Path]:
    return [Path(file) for file in file_list if file.suffix in {".so", ".pyd"}]


def create_hiddenimports() -> list[str]:
    res = ["queue", "mypy_extensions", "__future__"]

    try:
        files_list = package_files("psygnal")
    except PackageNotFoundError:
        return res

    if files_list is None:
        return res

    modules = binary_files(files_list)

    if len(modules) < 2:
        # This is a workaround for a bug in importlib.metadata in editable mode

        src_path = PSYGNAL_DIR.parent

        modules = [
            x.relative_to(src_path)
            for x in binary_files(PSYGNAL_DIR.iterdir())
            + binary_files(src_path.iterdir())
        ]

    for module in modules:
        res.append(str(module).split(".")[0].replace("/", ".").replace("\\", "."))

    return res


hiddenimports = create_hiddenimports()
