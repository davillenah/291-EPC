"""Engines stay light: the calculation engines use only the standard library, and every third-party import of an engine is declared in its pyproject.toml.

Why: a light engine starts fast, installs anywhere and has nothing to keep up to date. Heavy libraries (CAD, PDF, Office) live only in the engines that need them.
Run: python -m unittest discover -s harness/tests/architecture
"""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "harness" / "tools"))
sys.path.insert(0, str(REPO / "harness" / "tools" / "build"))
import impact_map as IM  # noqa: E402

STDLIB_ONLY = ("calc_common", "load_balance", "voltage_drop", "feeder_sizing", "short_circuit", "grounding", "selectivity", "transformer_sizing",
               "hvac", "receptacles", "boq", "datasheets", "rfq", "terminal_blocks", "design_basis", "descriptive_report", "calc_check", "symbols")
NAMESPACE_IMPORTS = {"engines"}            # `engines` is the folder name used in a few path-based imports, not a package to install
DIST_OF_IMPORT = {"PIL": "pillow", "docx": "python-docx", "yaml": "pyyaml"}


class EngineDependencies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _edges, cls.third = IM.scan()

    def test_the_light_engines_import_nothing_outside_the_standard_library(self):
        for unit in STDLIB_ONLY:
            with self.subTest(engine=unit):
                self.assertEqual(sorted(self.third.get(unit, set()) - NAMESPACE_IMPORTS), [])

    def test_every_third_party_import_is_declared(self):
        for unit in IM.engine_units():
            required, optional = IM.project_requirements(unit)
            declared = required | optional
            used = {DIST_OF_IMPORT.get(m, m).lower().replace("_", "-") for m in self.third.get(unit, set()) - NAMESPACE_IMPORTS}
            with self.subTest(engine=unit):
                self.assertEqual(sorted(used - declared), [], f"{unit}: add these to its pyproject.toml")


if __name__ == "__main__":
    unittest.main()
