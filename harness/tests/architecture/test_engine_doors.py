"""Public door per engine (COD-02): `epc_x.api` lists what an engine offers; everything else in the package is internal.

* Every engine with an `api.py` has an `__all__` there equal to the one in `epc_x/__init__.py`, and every name in it exists.
* The ratchet: code outside an engine that imports an internal module of it (`from epc_x.registry import ...`) is listed in `internal_imports_baseline.json`.
  A new internal import fails; the list only shrinks (an entry whose import is gone must be removed).
Re-record after removing imports: python harness/tests/architecture/test_engine_doors.py --write
Run: python -m unittest discover -s harness/tests/architecture
"""
import ast
import functools
import importlib
import json
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HARNESS = REPO / "harness"
ENGINES = HARNESS / "src" / "engines"
BASELINE = Path(__file__).with_name("internal_imports_baseline.json")
ROOTS = [HARNESS / "src", HARNESS / "tools", HARNESS / "tests"]
SKIP_PARTS = {"__pycache__", "golden", "golden_projects"}


@functools.lru_cache(maxsize=None)
def doors():
    return {p.parent.name: p.parent for p in sorted(ENGINES.glob("*/*/src/epc_*/api.py"))}


def internal_imports():
    """{"importer file::module"} for every import of `epc_x.<internal>` made from outside package epc_x (api.py of the engine itself excluded)."""
    names = set(doors())
    found = set()
    for root in ROOTS:
        for path in sorted(root.rglob("*.py")):
            if SKIP_PARTS & set(path.parts) or path.resolve() == Path(__file__).resolve():
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8-sig"))
            except SyntaxError:
                continue
            rel = path.relative_to(REPO).as_posix()
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    mods = [node.module]
                elif isinstance(node, ast.Import):
                    mods = [a.name for a in node.names]
                for mod in mods:
                    top, _, rest = mod.partition(".")
                    if top in names and rest and rest != "api":
                        own = f"/{top}/" in "/" + rel
                        if not own:
                            found.add(f"{rel}::{mod}")
    return sorted(found)


class EngineDoors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for src in ENGINES.glob("*/*/src"):
            if str(src) not in sys.path:
                sys.path.insert(0, str(src))

    def test_every_door_matches_the_package(self):
        self.assertGreaterEqual(len(doors()), 29)
        for name in doors():
            with self.subTest(engine=name):
                pkg = importlib.import_module(name)
                api = importlib.import_module(name + ".api")
                self.assertEqual(sorted(api.__all__), sorted(getattr(pkg, "__all__", [])))
                for item in api.__all__:
                    self.assertTrue(hasattr(api, item), f"{name}.api has no {item}")
                    self.assertTrue(hasattr(pkg, item), f"{name} has no {item}")

    def test_no_new_internal_import(self):
        recorded = set(json.loads(BASELINE.read_text(encoding="utf-8")))
        now = set(internal_imports())
        self.assertEqual(sorted(now - recorded), [], "new import of an engine's internal module: use `epc_x` (its door, api.py) or add the name to api.py")
        self.assertEqual(sorted(recorded - now), [], "import gone: take it off internal_imports_baseline.json (--write)")


if __name__ == "__main__":
    if "--write" in sys.argv:
        BASELINE.write_text(json.dumps(internal_imports(), indent=1) + "\n", encoding="utf-8")
        print("written", len(internal_imports()))
    else:
        unittest.main()
