import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))
BLACKLIST = [".venv"]


def all_module_names():
    modules = set()
    for subdir in ["NossiPack", "NossiSite", "NossiInterface"]:
        for py_file in (ROOT / subdir).rglob("*.py"):
            if any(b in py_file.parts for b in BLACKLIST):
                continue

            if py_file.name == "__init__.py":
                module_name = ".".join(py_file.parent.relative_to(ROOT).parts)
            else:
                module_name = ".".join(py_file.with_suffix("").relative_to(ROOT).parts)

            modules.add(module_name)

    return sorted(modules)


@pytest.mark.parametrize("module_name", all_module_names())
def test_module_importable(module_name):
    """Each module should import successfully."""
    importlib.import_module(module_name)
