"""MIG-33a: import rules of the platform layer (AST scan).

`epc_platform` modules import only the standard library, `epc_platform.*`, `disciplines.*` and engine packages `epc_*`.
`disciplines` never imports `epc_platform` (the existing discipline test accepts any `epc_*` name, so this rule is checked here).
Nothing under harness/src/platform/epc_platform or harness/src/disciplines imports `parked` or the old backend package `epc`.

  python -m unittest harness/tests/architecture/test_platform_imports.py
"""
import sys
import unittest
from pathlib import Path

from test_discipline_imports import FORBIDDEN_ROOTS, imported_roots

SRC = Path(__file__).resolve().parents[2] / "src"
PLATFORM = SRC / "platform" / "epc_platform"
DISCIPLINES = SRC / "disciplines"


def platform_violations(source):
    bad = []
    for name in imported_roots(source):
        top = name.split(".")[0]
        if name.startswith(".") or top in sys.stdlib_module_names or top in ("epc_platform", "disciplines") or (top.startswith("epc_") and top != "epc_mcp"):
            continue
        bad.append(f"{name}: " + ("forbidden" if top in FORBIDDEN_ROOTS else "not stdlib, epc_platform, disciplines or an epc_* engine"))
    return bad


def imports_platform(source):
    return [n for n in imported_roots(source) if n.split(".")[0] == "epc_platform"]


class PlatformImports(unittest.TestCase):
    def test_every_platform_module_respects_the_import_rules(self):
        files = sorted(PLATFORM.rglob("*.py"))
        self.assertTrue(files)
        for path in files:
            with self.subTest(module=path.relative_to(PLATFORM).as_posix()):
                self.assertEqual(platform_violations(path.read_text(encoding="utf-8")), [])

    def test_disciplines_do_not_import_the_platform(self):
        for path in sorted(DISCIPLINES.rglob("*.py")):
            with self.subTest(module=path.relative_to(DISCIPLINES).as_posix()):
                self.assertEqual(imports_platform(path.read_text(encoding="utf-8")), [])

    def test_nothing_imports_parked_or_the_backend(self):
        for path in sorted(PLATFORM.rglob("*.py")) + sorted(DISCIPLINES.rglob("*.py")):
            with self.subTest(module=path.name):
                tops = {n.split(".")[0] for n in imported_roots(path.read_text(encoding="utf-8"))}
                self.assertEqual(tops & set(FORBIDDEN_ROOTS), set())

    def test_the_platform_has_no_package_named_platform(self):
        self.assertFalse((SRC / "platform" / "__init__.py").exists())
        self.assertTrue((PLATFORM / "__init__.py").is_file())

    def test_the_scanner_catches_each_kind_of_violation(self):
        self.assertEqual(platform_violations("import os\nfrom epc_platform.events import log\nfrom disciplines.electrical_lv import store\nimport epc_drawing"), [])
        for src in ("import parked.web", "from epc.core import db", "import jsonschema", "import epc_mcp"):
            with self.subTest(src=src):
                self.assertTrue(platform_violations(src))
        self.assertTrue(imports_platform("from epc_platform.events import log"))
        self.assertEqual(imports_platform("import os"), [])


if __name__ == "__main__":
    unittest.main()
