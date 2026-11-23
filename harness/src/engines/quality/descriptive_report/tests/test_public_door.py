"""COD-02: `epc_descriptive_report.api` offers exactly what the package exports."""
import importlib
import unittest

import epc_descriptive_report


class PublicDoor(unittest.TestCase):
    def test_door_matches_package(self):
        api = importlib.import_module("epc_descriptive_report.api")
        self.assertEqual(sorted(api.__all__), sorted(epc_descriptive_report.__all__))
        for name in api.__all__:
            self.assertIs(getattr(api, name), getattr(epc_descriptive_report, name))


if __name__ == "__main__":
    unittest.main()
