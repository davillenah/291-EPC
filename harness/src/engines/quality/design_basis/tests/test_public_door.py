"""COD-02: `epc_design_basis.api` offers exactly what the package exports."""
import importlib
import unittest

import epc_design_basis


class PublicDoor(unittest.TestCase):
    def test_door_matches_package(self):
        api = importlib.import_module("epc_design_basis.api")
        self.assertEqual(sorted(api.__all__), sorted(epc_design_basis.__all__))
        for name in api.__all__:
            self.assertIs(getattr(api, name), getattr(epc_design_basis, name))


if __name__ == "__main__":
    unittest.main()
