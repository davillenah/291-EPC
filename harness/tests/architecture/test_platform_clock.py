"""MIG-33c: the system clock is read in ONE place of the platform: `cli/main.py` (`utc_now`). Everything else receives a clock as a parameter.

  python -m unittest harness/tests/architecture/test_platform_clock.py
"""
import ast
import unittest
from pathlib import Path

PLATFORM = Path(__file__).resolve().parents[2] / "src" / "platform" / "epc_platform"
ALLOWED = {"cli/main.py"}
CLOCK_CALLS = {"datetime": {"now", "utcnow", "today"}, "date": {"today"}, "time": {"time", "time_ns", "monotonic", "perf_counter", "localtime", "gmtime"}}


def clock_reads(source):
    """Line numbers of `datetime.now()`, `datetime.utcnow()`, `date.today()`, `time.time()`... (also `datetime.datetime.now()`) and of `from time import time`."""
    lines = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner = node.func.value
            name = owner.id if isinstance(owner, ast.Name) else owner.attr if isinstance(owner, ast.Attribute) else None
            if node.func.attr in CLOCK_CALLS.get(name, ()):
                lines.append(node.lineno)
        elif isinstance(node, ast.ImportFrom) and node.module == "time" and any(a.name in CLOCK_CALLS["time"] for a in node.names):
            lines.append(node.lineno)
    return sorted(lines)


class PlatformClock(unittest.TestCase):
    def test_only_the_cli_entry_point_reads_the_system_clock(self):
        found = {p.relative_to(PLATFORM).as_posix() for p in PLATFORM.rglob("*.py") if clock_reads(p.read_text(encoding="utf-8"))}
        self.assertEqual(found, ALLOWED)

    def test_the_scanner_finds_each_kind_of_read(self):
        for src in ("datetime.now()", "datetime.utcnow()", "date.today()", "time.time()", "datetime.datetime.now(tz)", "import time\ntime.monotonic()",
                    "from time import time"):
            with self.subTest(src=src):
                self.assertTrue(clock_reads(src), src)

    def test_the_scanner_ignores_other_calls(self):
        for src in ("clock()", "self.clock.now()", "x.time()", "json.dumps(1)", "from time import sleep", "datetime.fromisoformat(s)", "now()"):
            with self.subTest(src=src):
                self.assertEqual(clock_reads(src), [], src)


if __name__ == "__main__":
    unittest.main()
