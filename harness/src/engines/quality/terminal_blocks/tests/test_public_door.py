"""COD-02: `epc_terminal_blocks.api` offers exactly what the package exports."""
import importlib
import unittest

import epc_terminal_blocks


class PublicDoor(unittest.TestCase):
    def test_door_matches_package(self):
        api = importlib.import_module("epc_terminal_blocks.api")
        self.assertEqual(sorted(api.__all__), sorted(epc_terminal_blocks.__all__))
        for name in api.__all__:
            self.assertIs(getattr(api, name), getattr(epc_terminal_blocks, name))


if __name__ == "__main__":
    unittest.main()
