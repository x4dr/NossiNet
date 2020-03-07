import importlib.util
import re
from pathlib import Path
from typing import List
from unittest import TestCase


class TestIndependency(TestCase):
    modules: List[Path] = []

    @classmethod
    def setUpClass(cls) -> None:
        Path("~/token.discord").expanduser().touch()
        fileblacklist = ["setup.py"]
        patternblacklist = [r".*/\.?venv/.*"]
        cls.modules = []
        candidates = list(Path.cwd().glob("../**/*.py"))
        candidates = [
            x.relative_to(Path.cwd()) for x in candidates if x.name not in fileblacklist
        ]
        for pattern in patternblacklist:
            for m in candidates:
                if not re.match(pattern, m.as_posix()):
                    cls.modules.append(m)

    def test_loadability(self):
        """establish that each module is loadable and has no circular reference issues"""
        for module in TestIndependency.modules:
            if module.stem in ["extra", "views", "chat", "wiki"]:
                continue  # these dont need to be individually loadable, as they register endpoints and collide
            try:
                with self.subTest(msg=f"Loading {module.as_posix()[3:-3]} "):
                    spec = importlib.util.spec_from_file_location(
                        module.parent.stem + "." + module.stem, module
                    )
                    foo = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(foo)
            except ImportError as e:
                raise e
            except:
                raise
