"""The single-line generator only draws: it needs the calculation, and finds its symbols and title blocks in their own packages."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINES = HERE.parents[2]                                    # harness/src/engines: one folder per group (cad, calculation, ...)
SRC = [str(d) for d in sorted(ENGINES.glob("*/*/src"))]    # every engine: the generator imports the calculation engines, which import each other


class TestSldPackage(unittest.TestCase):
    def test_the_symbol_library_comes_from_epc_symbols(self):
        sys.path[:0] = SRC
        from epc_draw.symbols import library_dir
        self.assertTrue((Path(library_dir("sld-lv-symbol")) / "_catalog.json").is_file())

    def test_without_the_calculation_it_refuses_to_draw(self):
        with tempfile.TemporaryDirectory() as t:
            env = {"PYTHONPATH": os.pathsep.join(SRC), "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")}
            res = subprocess.run([sys.executable, "-m", "epc_draw.sld.sld_generator", "default", "x.xlsx", t, "SLD_X", "default", "default"], capture_output=True, text=True, env=env, cwd=t)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("SLD_CALC_JSON", res.stdout + res.stderr)

class TestBackupKind(unittest.TestCase):
    def test_the_source_of_a_feeder_tells_a_generator_from_a_ups_from_the_utility(self):
        from epc_draw.sld.sld_generator import backup_kind
        self.assertEqual([backup_kind(x) for x in ("Grupo electrógeno", "Generator set", "UPS 20 kVA", "Red", "", None, "groups")], ["gen", "gen", "ups", "", "", "", ""])


if __name__ == "__main__":
    unittest.main()


class TestImport(unittest.TestCase):
    def test_importing_the_generator_runs_nothing(self):
        sys.path[:0] = SRC
        import importlib
        before = set(os.listdir("."))
        module = importlib.import_module("epc_draw.sld.sld_generator")
        self.assertTrue(callable(module.generate) and callable(module.main))
        self.assertEqual(set(os.listdir(".")), before)                          # no file was written, no argument was read
