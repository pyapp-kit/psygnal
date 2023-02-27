from pathlib import Path
from typing import List

CURRENT_DIR = Path(__file__).parent


def get_hook_dirs() -> List[str]:
    return [str(CURRENT_DIR)]
