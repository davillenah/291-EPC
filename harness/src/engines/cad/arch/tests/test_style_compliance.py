"""Every layer, pen, linetype and text style a drawing uses exists in `epc_style.json`; names follow the English convention."""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from epc_arch import Options, recognize                          # noqa: E402
from epc_arch.drawing import TextItem, build_drawing, load_style   # noqa: E402
import helpers                                                    # noqa: E402


class TestStyleCompliance(unittest.TestCase):
    def setUp(self):
        self.style = load_style()
        self.drawing = build_drawing(recognize(helpers.room_dxf(), "flat.dxf", Options()).architecture)

    def test_every_layer_used_is_in_the_style(self):
        for it in self.drawing.items:
            self.assertIn(it.layer, self.style.layers)

    def test_every_pen_and_linetype_of_the_style_exists(self):
        for spec in self.style.layers.values():
            self.assertIn(spec.linetype, self.style.linetypes)
            if spec.pen:
                self.assertIn(spec.pen, self.style.pens)

    def test_every_text_style_used_exists(self):
        for it in self.drawing.items:
            if isinstance(it, TextItem):
                self.assertIn(it.style, self.style.text_styles)

    def test_names_follow_the_convention(self):
        for name in self.style.layers:
            self.assertRegex(name, r"^A-[A-Z]+(-[A-Z]+)*$")
        for name in self.style.pens:
            self.assertRegex(name, r"^pen_\d{3}$")
        for name in self.style.text_styles:
            self.assertRegex(name, r"^TXT_\d+$")

    def test_colours_are_greys(self):
        for spec in self.style.layers.values():
            h = spec.hex.lstrip("#")
            self.assertEqual(h[0:2], h[2:4], spec.name)
            self.assertEqual(h[2:4], h[4:6], spec.name)

    def test_default_sheet_is_a1_at_1_to_100(self):
        self.assertEqual((self.drawing.sheet, self.drawing.scale), ("A1", 100))
        self.assertTrue(re.match(r"^A[0-4]$", self.drawing.sheet))


if __name__ == "__main__":
    unittest.main()
