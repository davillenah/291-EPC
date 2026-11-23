"""COD-02: `epc_rules.api` offers exactly what the package exports."""
import importlib
import unittest

import epc_rules


class PublicDoor(unittest.TestCase):
    def test_door_matches_package(self):
        api = importlib.import_module("epc_rules.api")
        self.assertEqual(sorted(api.__all__), sorted(epc_rules.__all__))
        for name in api.__all__:
            self.assertIs(getattr(api, name), getattr(epc_rules, name))


if __name__ == "__main__":
    unittest.main()
