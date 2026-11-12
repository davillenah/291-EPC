"""A CAD export that labels the glyphs with bytes leaves a text layer with the UTF-8 bytes of each character read one by one (`Ã‘` for `Ñ`, `Â·` for `·`, `Â²` for `²`): the engine reads the character."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from epc_arch.sources.pdf import _repaired                       # noqa: E402


def _box(i):
    return (float(i), 0.0, i + 1.0, 1.0)


class TestPdfTextRepair(unittest.TestCase):
    def test_pairs_of_bytes_become_the_character(self):
        text = "BAÃ‘O PT-01 Â· 8,75 mÂ²"
        fixed, boxes = _repaired(text, [_box(i) for i in range(len(text))])
        self.assertEqual(fixed, "BAÑO PT-01 · 8,75 m²")
        self.assertEqual(len(fixed), len(boxes))
        self.assertEqual(boxes[2], (2.0, 0.0, 4.0, 1.0))                  # the box of the merged character is the two together

    def test_a_text_that_is_right_is_left_alone(self):
        text = "BAÑO 8,75 m² Ángel"
        fixed, boxes = _repaired(text, [_box(i) for i in range(len(text))])
        self.assertEqual(fixed, text)
        self.assertEqual(len(boxes), len(text))


if __name__ == "__main__":
    unittest.main()
