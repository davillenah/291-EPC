"""Modules under harness/src/disciplines stay thin (seed of MIG-34).

They import nothing from parked/web, no other discipline, and only the standard library, `disciplines.<own discipline>`
or an engine package `epc_*` (AST scan).
"""
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "src" / "disciplines"
FORBIDDEN_ROOTS = ("parked", "web", "backend", "epc", "frontend")


def imported_roots(source):
    """Dotted names imported by a module (relative imports are returned as '.' + module)."""
    names = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names.append("." * node.level + (node.module or ""))
    return names


def violations(source, own):
    """Imports of one module of discipline `own` that break the rules."""
    bad = []
    for name in imported_roots(source):
        top = name.split(".")[0]
        if name.startswith(".") or top in sys.stdlib_module_names or top.startswith("epc_"):
            continue
        if top == "disciplines":
            parts = name.split(".")
            if len(parts) > 1 and parts[1] != own:
                bad.append(f"{name}: another discipline")
            continue
        bad.append(f"{name}: " + ("forbidden" if top in FORBIDDEN_ROOTS else "not stdlib, disciplines or epc_*"))
    return bad


class DisciplineImports(unittest.TestCase):
    def test_every_discipline_module_respects_the_import_rules(self):
        for path in sorted(ROOT.rglob("*.py")):
            own = path.relative_to(ROOT).parts[0]
            with self.subTest(module=path.relative_to(ROOT).as_posix()):
                self.assertEqual(violations(path.read_text(encoding="utf-8"), own), [])

    def test_disciplines_is_a_namespace_package_and_the_discipline_is_a_package(self):
        self.assertFalse((ROOT / "__init__.py").exists())
        for sub in ("", "intake", "requirements", "stages", "rules"):
            self.assertTrue((ROOT / "electrical_lv" / sub / "__init__.py").is_file(), sub)

    def test_the_scanner_catches_each_kind_of_violation(self):
        src = "import os\nimport epc_drawing\nfrom disciplines.electrical_lv.intake import x\nfrom . import y\n"
        self.assertEqual(violations(src, "electrical_lv"), [])
        self.assertTrue(violations("import parked.web.x", "electrical_lv"))
        self.assertTrue(violations("from epc.core import db", "electrical_lv"))
        self.assertTrue(violations("from disciplines.electrical_mv import z", "electrical_lv"))
        self.assertTrue(violations("import jsonschema", "electrical_lv"))


if __name__ == "__main__":
    unittest.main()
