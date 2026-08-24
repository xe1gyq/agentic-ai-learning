"""Import lesson scripts by file path, including folders whose names start with digits."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_lesson_module(module_name: str, relative_path: str) -> ModuleType:
    """Load a lesson module without executing its guarded CLI entry point."""
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load lesson module from {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

