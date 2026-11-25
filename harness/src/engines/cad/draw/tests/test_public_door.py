"""COD-02: `epc_symbols.api` offers exactly what the package exports."""
import importlib
import unittest

from epc_draw import symbols as epc_symbols


class PublicDoor(unittest.TestCase):
    def test_door_matches_package(self):
        api = importlib.import_module("epc_draw.symbols.api")
        self.assertEqual(sorted(api.__all__), sorted(epc_symbols.__all__))
        for name in api.__all__:
            self.assertIs(getattr(api, name), getattr(epc_symbols, name))


if __name__ == "__main__":
    unittest.main()
