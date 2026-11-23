"""COD-10: gradual static typing. The modules listed here are fully annotated and must stay clean under mypy; add a module to the list once it is annotated, never remove one.

  python -m pytest harness/tests/architecture/test_typed_modules.py     (the engines and harness/src on PYTHONPATH, as in the gate)
"""
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TYPED_MODULES = (
    "harness/src/engines/calculation/transformer_sizing/src/epc_transformer_sizing/sizing.py",
    "harness/src/engines/calculation/voltage_drop/src/epc_voltage_drop/voltage_drop.py",
    "harness/src/engines/calculation/load_balance/src/epc_load_balance/current_and_loads.py",
)
FLAGS = ("--disallow-untyped-defs", "--disallow-incomplete-defs", "--ignore-missing-imports", "--follow-imports=silent", "--no-error-summary", "--cache-dir=" + str(REPO / "tmp" / ".mypy_cache"))


class TypedModules(unittest.TestCase):
    def test_every_listed_module_exists(self):
        for module in TYPED_MODULES:
            self.assertTrue((REPO / module).is_file(), module)

    def test_the_listed_modules_are_clean_under_mypy(self):
        run = subprocess.run([sys.executable, "-m", "mypy", *FLAGS, *TYPED_MODULES], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, f"mypy found problems (is mypy installed? see requirements-dev.txt):\n{run.stdout}{run.stderr}")


if __name__ == "__main__":
    unittest.main()
