"""COD-02: `epc_calc_check.api` offers exactly what the package exports."""
import importlib
import unittest

import epc_calc_check


class PublicDoor(unittest.TestCase):
    def test_door_matches_package(self):
        api = importlib.import_module("epc_calc_check.api")
        self.assertEqual(sorted(api.__all__), sorted(epc_calc_check.__all__))
        for name in api.__all__:
            self.assertIs(getattr(api, name), getattr(epc_calc_check, name))


if __name__ == "__main__":
    unittest.main()
