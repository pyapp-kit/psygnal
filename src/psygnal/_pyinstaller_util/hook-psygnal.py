import contextlib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import files as package_files

hiddenimports = ["mypy_extensions"]

with contextlib.suppress(PackageNotFoundError):
    files_list = package_files("psygnal")

    if files_list is not None:
        for package_path in files_list:
            if package_path.suffix in {".so", ".pyd"}:
                hiddenimports.append(
                    package_path.name.split(".")[0].replace("/", ".").replace("\\", ".")
                )


hiddenimports.append("mypy_extensions")
