from pathlib import Path

CURRENT_DIR = Path(__file__).parent


def get_hook_dirs() -> list[str]:
    return [str(CURRENT_DIR)]
