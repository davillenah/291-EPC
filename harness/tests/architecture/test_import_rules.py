"""MIG-34: the dependency rules of PRD 14.4 as architecture tests (AST scans).

1. No imports between disciplines: every folder under `harness/src/disciplines/` (electrical_lv today, electrical_mv tomorrow) imports no other
   discipline. Generic over the folders that exist, with a self-test on a synthetic second discipline.
2. Disciplines import engines, never the reverse: no engine package (`harness/src/engines/**/src/epc_*`) imports `disciplines`, `epc_platform`
   or `epc_mcp`.
3. Nothing under `harness/` imports the parked web application (the old backend package `epc`, or `parked`). MIG-38 removed the last five importers, so
   the allowlist `PARKED_IMPORTERS` is empty (MIG-38 done) and the test fails on ANY file that imports it. The generated report of what the harness takes
   from the web is `harness/docs/architecture/PARKED_IMPORTS.md` (`harness/tools/build/parked_imports.py`; `--check` runs here too, inside the gate's `harness-tests`).

  python -m pytest harness/tests/architecture/test_import_rules.py
"""
import ast
import sys
import unittest
from pathlib import Path

from test_discipline_imports import imported_roots

HARNESS = Path(__file__).resolve().parents[2]
DISCIPLINES = HARNESS / "src" / "disciplines"
ENGINES = HARNESS / "src" / "engines"
ENGINE_FORBIDDEN = ("disciplines", "epc_platform", "epc_mcp")
PARKED_ROOTS = ("epc", "parked")
SCANNED = ("src", "tests", "tools", ".claude")
SKIPPED_PARTS = ("node_modules", "__pycache__", ".venv")
# Files that cannot be parsed today (not Python 3 syntax); a new entry needs a reason.
UNPARSEABLE = {"tools/migrate/generate_project_files.py"}

# Empty since MIG-38b: no file under harness/ imports the parked web application. A new entry would be a regression; paths are relative to harness/.
PARKED_IMPORTERS = frozenset()


def read_names(path):
    """Dotted imports of a file (UTF-8, with or without BOM); None when the file is not parseable Python."""
    try:
        return imported_roots(path.read_text(encoding="utf-8-sig"))
    except SyntaxError:
        return None


def other_disciplines(names, own):
    """Imports of `disciplines.<x>` with x different from `own` (also `import disciplines` bare)."""
    bad = []
    for name in names:
        parts = name.split(".")
        if parts[0] == "disciplines" and (len(parts) == 1 or parts[1] != own):
            bad.append(name)
    return bad


def forbidden_in_engine(names):
    return [n for n in names if n.split(".")[0] in ENGINE_FORBIDDEN]


def imports_parked(names):
    return [n for n in names if n.split(".")[0] in PARKED_ROOTS]


def python_files(base):
    return sorted(p for p in base.rglob("*.py") if not set(p.parts) & set(SKIPPED_PARTS))


def engine_sources():
    """Every .py file of the engine packages (harness/src/engines/**/src/**)."""
    return [p for p in python_files(ENGINES) if "src" in p.relative_to(ENGINES).parts]


def parked_importers_found():
    found = set()
    unparseable = set()
    for folder in SCANNED:
        for path in python_files(HARNESS / folder):
            names = read_names(path)
            rel = path.relative_to(HARNESS).as_posix()
            if names is None:
                unparseable.add(rel)
            elif imports_parked(names):
                found.add(rel)
    return found, unparseable


class NoImportsBetweenDisciplines(unittest.TestCase):
    def disciplines(self):
        return sorted(p for p in DISCIPLINES.iterdir() if p.is_dir() and p.name != "__pycache__")

    def test_there_is_at_least_one_discipline(self):
        self.assertIn("electrical_lv", [p.name for p in self.disciplines()])

    def test_no_discipline_imports_another(self):
        for folder in self.disciplines():
            for path in python_files(folder):
                with self.subTest(module=path.relative_to(DISCIPLINES).as_posix()):
                    names = read_names(path)
                    self.assertIsNotNone(names)
                    self.assertEqual(other_disciplines(names, folder.name), [])

    def test_the_check_catches_a_second_discipline_importing_the_first(self):
        source = "from disciplines.electrical_lv.store import ProjectStore\nimport disciplines\nfrom disciplines import electrical_lv\n"
        names = imported_roots(source)
        self.assertEqual(len(other_disciplines(names, "electrical_mv")), 3)
        self.assertEqual(other_disciplines(imported_roots("from disciplines.electrical_mv.x import y"), "electrical_mv"), [])
        self.assertEqual(other_disciplines(imported_roots("import os\nimport epc_drawing"), "electrical_mv"), [])

    def test_a_synthetic_violation_in_a_second_discipline_folder_is_found(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            second = Path(tmp) / "electrical_mv"
            second.mkdir()
            (second / "stage.py").write_text("from disciplines.electrical_lv import pipeline\n", encoding="utf-8")
            (second / "ok.py").write_text("import json\nfrom disciplines.electrical_mv import stage\n", encoding="utf-8")
            bad = {p.name: other_disciplines(read_names(p), "electrical_mv") for p in python_files(second)}
            self.assertEqual(bad, {"ok.py": [], "stage.py": ["disciplines.electrical_lv"]})


class DisciplinesImportEnginesNeverTheReverse(unittest.TestCase):
    def test_there_are_engine_sources_to_scan(self):
        files = engine_sources()
        self.assertGreater(len(files), 100)
        self.assertTrue(any("epc_aea90364" in p.parts for p in files))

    def test_no_engine_imports_disciplines_the_platform_or_the_mcp_server(self):
        for path in engine_sources():
            names = read_names(path)
            with self.subTest(module=path.relative_to(ENGINES).as_posix()):
                self.assertIsNotNone(names, "engine source that cannot be parsed")
                self.assertEqual(forbidden_in_engine(names), [])

    def test_the_check_catches_each_reverse_import(self):
        for source in ("import disciplines", "from disciplines.electrical_lv import store", "import epc_platform.api", "from epc_mcp import server"):
            with self.subTest(source=source):
                self.assertTrue(forbidden_in_engine(imported_roots(source)))
        self.assertEqual(forbidden_in_engine(imported_roots("import json\nfrom epc_core import x\nfrom . import y")), [])

    def test_disciplines_use_engines_through_epc_packages(self):
        used = set()
        for path in python_files(DISCIPLINES):
            used |= {n.split(".")[0] for n in read_names(path) if n.startswith("epc_")}
        self.assertTrue(used, "no discipline uses an engine: the rule would be vacuous")


if __name__ == "__main__":
    unittest.main()
