"""Drawing engines stay called functions (ADR-0038, ADR-0042): nothing new reads the environment, the current folder or the clock, starts a process or makes a temporary file.

* The drawing engines are `cad/*` (`dxf`, `symbols`, `titleblock`, `plan`, `arch`, `sld`, `mld`, `drawing`).
* Each file has a count per marker in `drawing_purity_baseline.json` (what it does today). A count may go down and may never go up; a file that is not in the baseline
  has none; when a count goes down, the baseline must be lowered (`python harness/tests/architecture/test_drawing_purity.py --update`), so the list only shrinks.
* Command-line adapters (`cli*.py`, `main` in `__main__.py`) hold the I/O by design and are counted like the rest, so their numbers also fall as the callers move to the functions.
Run: python -m unittest discover -s harness/tests/architecture
"""
import ast
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ENGINES = REPO / "harness" / "src" / "engines" / "cad"
BASELINE = Path(__file__).with_name("drawing_purity_baseline.json")
# marker -> the dotted names that count as one use of it
MARKERS = {
    "environment": {"os.environ", "os.getenv", "os.putenv"},
    "cwd": {"os.getcwd", "os.chdir", "Path.cwd", "pathlib.Path.cwd"},
    "process": {"subprocess"},
    "tempfile": {"tempfile"},
    "clock": {"datetime.now", "datetime.utcnow", "date.today", "datetime.date.today", "datetime.datetime.now", "datetime.datetime.utcnow", "time.time", "time.monotonic"},
}


def _dotted(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _uses(tree):
    found = Counter()
    for node in ast.walk(tree):
        name = _dotted(node) if isinstance(node, (ast.Attribute, ast.Name)) else None
        for marker, names in MARKERS.items():
            if name in names:
                found[marker] += 1
    return found


def measure():
    """{relative path: {marker: count}} of every drawing-engine source file that uses a marker."""
    out = {}
    for path in sorted(ENGINES.glob("*/src/epc_*/**/*.py")):
        rel = path.relative_to(REPO).as_posix()
        counts = _uses(ast.parse(path.read_text(encoding="utf-8-sig")))
        if counts:
            out[rel] = dict(sorted(counts.items()))
    return out


class DrawingPurity(unittest.TestCase):
    def test_nothing_grows_and_the_baseline_only_shrinks(self):
        base, now = json.loads(BASELINE.read_text(encoding="utf-8")), measure()
        grew = [f"{f}: {m} {base.get(f, {}).get(m, 0)} -> {n}" for f, c in now.items() for m, n in c.items() if n > base.get(f, {}).get(m, 0)]
        self.assertEqual(grew, [], "a drawing engine reads the environment, the folder or the clock, or starts a process: pass it as data (ADR-0042)")
        shrank = [f"{f}: {m} {n} -> {now.get(f, {}).get(m, 0)}" for f, c in base.items() for m, n in c.items() if now.get(f, {}).get(m, 0) < n]
        self.assertEqual(shrank, [], "lower the baseline: python harness/tests/architecture/test_drawing_purity.py --update")


if __name__ == "__main__":
    if "--update" in sys.argv:
        BASELINE.write_text(json.dumps(measure(), indent=1) + "\n", encoding="utf-8")
        print("baseline written")
    else:
        unittest.main()
