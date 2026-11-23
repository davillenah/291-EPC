"""Engine errors (ADR-0039, COD-21, GEN-08): every engine fails with its own error class built from a code with an English and a Spanish text.

* Every `messages.py` is complete: both languages, the same `{placeholders}` in both, snake_case codes.
* A `raise <Engine>Error("code", ...)` names a code its `messages.py` has.
* The ratchet: an engine that is converted raises no plain `ValueError` / `RuntimeError` / `Exception` with a message of its own. `UNCONVERTED` lists the engines still to convert;
  it may only shrink: an engine on it that no longer has a plain raise must be taken off the list.
Run: python -m unittest discover -s harness/tests/architecture
"""
import ast
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "harness" / "tools" / "build"))
import error_catalogue as EC  # noqa: E402

ENGINES = REPO / "harness" / "src" / "engines"
PLAIN = {"ValueError", "RuntimeError", "Exception"}
UNCONVERTED = {
    "epc_aea90364", "epc_arch", "epc_boq", "epc_calc_common", "epc_datasheets", "epc_descriptive_report", "epc_design_basis", "epc_documents", "epc_drawing", "epc_dxf", "epc_feeder_sizing", "epc_grounding", "epc_hvac", "epc_lighting", "epc_load_balance", "epc_plan", "epc_receptacles", "epc_rfq", "epc_selectivity", "epc_short_circuit", "epc_symbols", "epc_terminal_blocks", "epc_titleblock", "epc_transformer_sizing", "epc_voltage_drop",
}      # engines whose raises are still plain text (shrinks as COD-21 / GEN-08 converts them)


def packages():
    return {p.name: p for p in sorted(ENGINES.glob("*/*/src/epc_*")) if p.is_dir()}


def raises(package):
    """[(file, line, class name, first argument node or None)] of every `raise Name(...)` in the package (a bare `raise` or `raise e` is not one)."""
    found = []
    for path in sorted(package.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
            if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
                args = node.exc.args
                found.append((path.relative_to(REPO).as_posix(), node.lineno, node.exc.func.id, args[0] if args else None))
    return found


def own_errors(package):
    """The names of the error classes the package defines."""
    names = set()
    for path in package.rglob("*.py"):
        names |= {n.name for n in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))) if isinstance(n, ast.ClassDef) and n.name.endswith("Error")}
    return names


def loose(package):
    """The raises still written as text: a plain error with a message, or the engine's own error with a sentence (an f-string or a text that is not an `err_` code)."""
    mine = own_errors(package)
    found = []
    for file, line, cls, first in raises(package):
        sentence = isinstance(first, ast.JoinedStr) or (isinstance(first, ast.Constant) and isinstance(first.value, str) and not re.fullmatch(r"err_[a-z0-9_]+", first.value))
        if (cls in PLAIN and first is not None) or (cls in mine and sentence):
            found.append(f"{file}:{line}")
    return found


class MessageTables(unittest.TestCase):
    def test_every_message_has_both_languages_and_the_same_placeholders(self):
        for name, path in EC.message_files():
            for code, m in EC.read_messages(path).items():
                with self.subTest(engine=name, code=code):
                    self.assertRegex(code, r"^[a-z][a-z0-9_]*$")
                    self.assertEqual(set(m), {"en", "es"})
                    self.assertTrue(m["en"].strip() and m["es"].strip())
                    self.assertEqual(sorted(re.findall(r"\{(\w+)", m["en"])), sorted(re.findall(r"\{(\w+)", m["es"])))

    def test_every_literal_code_raised_exists(self):
        tables = {name: EC.read_messages(path) for name, path in EC.message_files()}
        for name, package in packages().items():
            if name not in tables:
                continue
            mine = own_errors(package)
            for file, line, cls, first in raises(package):
                if cls in mine and isinstance(first, ast.Constant) and isinstance(first.value, str):
                    with self.subTest(where=f"{file}:{line}"):
                        self.assertIn(first.value, tables[name], f"{cls}({first.value!r}) has no entry in {name}/messages.py")

    def test_an_error_code_is_not_a_sentence(self):
        for name, package in packages().items():
            if name not in dict(EC.message_files()):
                continue
            for file, line, cls, first in raises(package):
                if cls in own_errors(package) and isinstance(first, ast.Constant) and isinstance(first.value, str):
                    with self.subTest(where=f"{file}:{line}"):
                        self.assertRegex(first.value, r"^err_[a-z0-9_]+$")


class Ratchet(unittest.TestCase):
    def test_a_converted_engine_raises_no_plain_error_with_a_message(self):
        for name, package in packages().items():
            if name in UNCONVERTED:
                continue
            with self.subTest(engine=name):
                self.assertEqual(loose(package), [], "use the engine's own error with a code from messages.py (ADR-0039)")

    def test_the_unconverted_list_only_shrinks(self):
        pk = packages()
        for name in sorted(UNCONVERTED):
            with self.subTest(engine=name):
                self.assertIn(name, pk)
                self.assertTrue(loose(pk[name]), f"{name} has no raise written as text left: take it off UNCONVERTED")


if __name__ == "__main__":
    unittest.main()
