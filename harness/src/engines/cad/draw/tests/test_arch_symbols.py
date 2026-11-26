"""SYM-05: the architecture plan symbols (furniture, fixtures, openings) live in the symbol engine."""
import unittest
from pathlib import Path

from epc_draw.symbols import arch_symbols


class ArchSymbols(unittest.TestCase):
    def test_twenty_five_symbols_each_with_its_svg(self):
        rows = arch_symbols()
        self.assertEqual(len(rows), 25)
        for row in rows:
            self.assertTrue(Path(row["archivo"]).is_file(), row["nombre"])
            self.assertGreater(row["ancho_cm"], 0)

    def test_names_are_unique(self):
        names = [row["nombre"] for row in arch_symbols()]
        self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main()
