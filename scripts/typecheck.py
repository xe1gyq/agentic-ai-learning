"""Run mypy separately for standalone lesson scripts with repeated filenames."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

IGNORED_PARTS = {"venv", ".venv", ".git", "__pycache__"}


def discover_python_files(arguments: list[str]) -> list[Path]:
    """Expand files and directories into a sorted, duplicate-free Python file list."""
    discovered: set[Path] = set()
    for argument in arguments:
        path = Path(argument)
        candidates = path.rglob("*.py") if path.is_dir() else (path,)
        for candidate in candidates:
            if candidate.suffix == ".py" and not (set(candidate.parts) & IGNORED_PARTS):
                discovered.add(candidate)
    return sorted(discovered)


def main() -> int:
    """Type-check each file independently so repeated `agent.py` names do not collide."""
    files = discover_python_files(sys.argv[1:])
    if not files:
        print("No Python files to type-check.")
        return 0

    failed = False
    for path in files:
        result = subprocess.run(
            [sys.executable, "-m", "mypy", "--ignore-missing-imports", str(path)],
            check=False,
        )
        failed = failed or result.returncode != 0
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
