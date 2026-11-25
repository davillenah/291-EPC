"""COD-11: no code under harness/src swallows every error in silence (`except:` or `except Exception:` whose body only passes, continues or returns None).

Catch the error that is expected, or report it (a warning, a finding, a message in English and Spanish). A catch-all that re-raises or records the
error is allowed, and so is one that states on its line why silence is the intended behaviour (`# noqa: BLE001 - <reason>`). The one other exception is the FreeCAD macro, which runs inside FreeCAD (its OCC errors cannot be imported here).
Run: python -m unittest discover -s harness/tests/architecture
"""
import ast
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "harness" / "src"
REASON = re.compile(r"#\s*noqa:\s*BLE001\s+-\s+\S")                                  # the documented decision: "# noqa: BLE001 - <why>"
ALLOWED = {"harness/src/engines/cad/draw/src/epc_draw/pv/freecad.py"}     # FreeCAD macro: Part.OCCError exists only inside FreeCAD


def silent(body):
    return all(isinstance(n, (ast.Pass, ast.Continue)) or (isinstance(n, ast.Return) and (n.value is None or (isinstance(n.value, ast.Constant) and n.value.value is None)))
               for n in body)


def catch_all(handler):
    return handler.type is None or (isinstance(handler.type, ast.Name) and handler.type.id in ("Exception", "BaseException"))


def offenders():
    found = []
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(REPO).as_posix()
        if "/tests/" in rel or rel in ALLOWED:
            continue
        text = path.read_text(encoding="utf-8-sig")
        lines = text.splitlines()
        tree = ast.parse(text, filename=rel)
        found += [f"{rel}:{n.lineno}" for n in ast.walk(tree)
                  if isinstance(n, ast.ExceptHandler) and catch_all(n) and silent(n.body) and not REASON.search(lines[n.lineno - 1])]
    return found


class NoSilentCatchAll(unittest.TestCase):
    def test_no_error_is_swallowed_in_silence(self):
        self.assertEqual(offenders(), [], "catch the expected error or report it (COD-11)")

    def test_the_rule_sees_a_silent_catch_all(self):
        tree = ast.parse("try:\n    f()\nexcept Exception:\n    pass\n")
        handler = next(n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler))
        self.assertTrue(catch_all(handler) and silent(handler.body))


if __name__ == "__main__":
    unittest.main()
