"""Render @overload for SignalInstance.connect."""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from jinja2 import Template

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

template: Template = Template(TEMPLATE_PATH.read_text())
result = template.render(number_of_types=MAX_ARGS, connect_overloads=connect_overloads)

result = (
    "# WARNING: do not modify this code, it is generated by "
    f"{TEMPLATE_PATH.name}\n\n" + result
)

# make a temporary file to write to
with NamedTemporaryFile(suffix=".py") as tmp:
    Path(tmp.name).write_text(result)
    subprocess.run(["ruff", "format", tmp.name])  # noqa
    subprocess.run(["ruff", "check", tmp.name, "--fix"])  # noqa
    result = Path(tmp.name).read_text()

current_content = DEST_PATH.read_text() if DEST_PATH.exists() else ""
if current_content != result and os.getenv("CHECK_JINJA"):
    raise RuntimeError(f"{DEST_PATH} content not up to date with {TEMPLATE_PATH.name}")

DEST_PATH.write_text(result)
