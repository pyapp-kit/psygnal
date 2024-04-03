"""Build _signal.pyi with def connect @overloads."""

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import indent

ROOT = Path(__file__).parent.parent / "src" / "psygnal"
TEMPLATE_PATH = ROOT / "_signal.py.jinja2"
DEST_PATH = TEMPLATE_PATH.with_suffix("")

# Maximum number of arguments allowed in callbacks
MAX_ARGS = 5


@dataclass
class Arg:
    """Single arg."""

    name: str
    hint: str
    default: str | None = None


@dataclass
class Sig:
    """Full signature."""

    arguments: list[Arg]
    return_hint: str

    def render(self) -> str:
        """Render the signature as a def connect overload."""
        args = ", ".join(f"{arg.name}: {arg.hint}" for arg in self.arguments) + ","
        args += """
        *,
        thread: threading.Thread | Literal["main", "current"] | None = None,
        check_nargs: bool | None = None,
        check_types: bool | None = None,
        unique: bool | str = False,
        max_args: int | None = None,
        on_ref_error: RefErrorChoice = "warn",
        priority: int = 0,
        """
        return f"\n@overload\ndef connect({args}) -> {self.return_hint}: ..."


connect_overloads: list[Sig] = []
for nself in range(MAX_ARGS + 1):
    for ncallback in range(nself + 1):
        if nself:
            self_types = ", ".join(f"type[_T{i+1}]" for i in range(nself))
        else:
            self_types = "()"
        arg_types = ", ".join(f"_T{i+1}" for i in range(ncallback))
        slot_type = f"Callable[[{arg_types}], RetT]"
        connect_overloads.append(
            Sig(
                arguments=[
                    Arg(name="self", hint=f"SignalInstance[{self_types}]"),
                    Arg(name="slot", hint=slot_type),
                ],
                return_hint=slot_type,
            )
        )

connect_overloads.append(
    Sig(
        arguments=[
            Arg(name="self", hint="SignalInstance[Unparametrized]"),
            Arg(name="slot", hint="F"),
        ],
        return_hint="F",
    )
)
connect_overloads.append(
    Sig(
        arguments=[
            Arg(name="self", hint="SignalInstance"),
        ],
        return_hint="Callable[[F], F]",
    )
)


STUB = Path("src/psygnal/_signal.pyi")


if __name__ == "__main__":
    existing_stub = STUB.read_text() if STUB.exists() else None

    # make a temporary file to write to
    with TemporaryDirectory() as tmpdir:
        subprocess.run(
            [  # noqa
                "stubgen",
                "--include-private",
                # "--include-docstrings",
                "src/psygnal/_signal.py",
                "-o",
                tmpdir,
            ]
        )
        stub_path = Path(tmpdir) / "psygnal" / "_signal.pyi"
        new_stub = "from typing import NewType\n" + stub_path.read_text()
        new_stub = new_stub.replace(
            "ReemissionVal: Incomplete",
            'ReemissionVal = Literal["immediate", "queued", "latest-only"]',
        )
        new_stub = new_stub.replace(
            "Unparametrized: Incomplete",
            'Unparametrized = NewType("Unparametrized", object)',
        )
        overloads = "\n".join(sig.render() for sig in connect_overloads)
        overloads = indent(overloads, "    ")
        new_stub = re.sub(r"def connect.+\.\.\.", overloads, new_stub)

        stub_path.write_text(new_stub)
        subprocess.run(["ruff", "format", tmpdir])  # noqa
        subprocess.run(["ruff", "check", tmpdir, "--fix"])  # noqa
        new_stub = stub_path.read_text()

    if os.getenv("CHECK_STUBS"):
        if existing_stub != new_stub:
            raise RuntimeError(f"{STUB} content not up to date.")
        sys.exit(0)

    STUB.write_text(new_stub)
