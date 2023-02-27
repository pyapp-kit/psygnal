from pathlib import Path
from typing import Iterable, List, Union

try:
    from importlib.metadata import PackageNotFoundError, PackagePath
    from importlib.metadata import files as package_files
except ImportError:
    from importlib_metadata import (  # type: ignore[no-redef]
        PackageNotFoundError,
        PackagePath,
    )
    from importlib_metadata import files as package_files  # type: ignore[no-redef]

CURRENT_DIR = Path(__file__).parent


def binary_files(file_list: Iterable[Union[PackagePath, Path]]) -> List[Path]:
    return [Path(file) for file in file_list if file.suffix in {".so", ".pyd"}]


def create_hiddenimports() -> List[str]:
    res = ["mypy_extensions", "__future__"]

    try:
        files_list = package_files("psygnal")
    except PackageNotFoundError:
        return res

    if files_list is None:
        return res

    modules = binary_files(files_list)

    if not modules:
        # This is a workaround for a bug in importlib.metadata in editable mode

        src_path = CURRENT_DIR.parent.parent

        modules = [
            x.relative_to(src_path)
            for x in binary_files(CURRENT_DIR.parent.iterdir())
            + binary_files(src_path.iterdir())
        ]

    for module in modules:
        res.append(str(module).split(".")[0].replace("/", ".").replace("\\", "."))

    return res


hiddenimports = create_hiddenimports()
