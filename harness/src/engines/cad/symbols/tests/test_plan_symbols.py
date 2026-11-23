"""SYM-04: the unit symbols of the electrical plan live in the symbol engine, not in `epc_plan`."""
import unittest

from epc_symbols import plan_symbols


class PlanSymbols(unittest.TestCase):
    def test_thirty_one_symbols_with_primitives_or_svg(self):
        symbols = plan_symbols()
        self.assertEqual(len(symbols), 31)
        for name, entry in symbols.items():
            self.assertTrue("prims" in entry or "svg" in entry, name)

    def test_each_call_is_a_fresh_copy(self):
        first = plan_symbols()
        first["camara"]["prims"].clear()
        self.assertTrue(plan_symbols()["camara"]["prims"])

    def test_svg_entries_point_to_a_file(self):
        from pathlib import Path
        for entry in plan_symbols().values():
            if "svg" in entry:
                self.assertTrue(Path(entry["svg"]).is_file())


if __name__ == "__main__":
    unittest.main()
