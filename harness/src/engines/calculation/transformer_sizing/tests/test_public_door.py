"""COD-02: `epc_transformer_sizing.api` offers exactly what the package exports."""
import importlib
import unittest

import epc_transformer_sizing


class PublicDoor(unittest.TestCase):
    def test_door_matches_package(self):
        api = importlib.import_module("epc_transformer_sizing.api")
        self.assertEqual(sorted(api.__all__), sorted(epc_transformer_sizing.__all__))
        for name in api.__all__:
            self.assertIs(getattr(api, name), getattr(epc_transformer_sizing, name))


if __name__ == "__main__":
    unittest.main()
