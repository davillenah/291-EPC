"""Every output of the engine is in Arial, and the DXF is in metres with the lower left corner of the sheet at the origin, its extents in the header and its text size in metres."""
import io
import sys
import unittest
from pathlib import Path

import ezdxf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from epc_arch import Options, recognize                          # noqa: E402
from epc_arch.drawing import build_drawing                        # noqa: E402
from epc_arch.export.export_dxf import to_dxf                     # noqa: E402
from epc_arch.export.export_raster import to_pdf                  # noqa: E402
from epc_arch.export.export_svg import to_svg                     # noqa: E402
import helpers                                                    # noqa: E402


class TestArialAndMetres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = recognize(helpers.room_dxf(), "flat.dxf", Options())
        cls.drawing = build_drawing(cls.result.architecture, sheet="A3")
        cls.doc = ezdxf.read(io.StringIO(to_dxf(cls.drawing)))

    def test_the_svgs_are_in_arial(self):
        self.assertIn('font-family="Arial,', to_svg(self.drawing))
        self.assertIn('font-family="Arial,', self.result.svg)

    def test_the_pdf_is_in_arial(self):
        pdf = to_pdf(self.drawing)
        self.assertIn(b"/BaseFont /ArialMT", pdf)
        self.assertNotIn(b"Helvetica", pdf)

    def test_the_dxf_text_styles_are_arial(self):
        fonts = {s.dxf.font for s in self.doc.styles}
        self.assertEqual(fonts, {"arial.ttf"})

    def test_the_dxf_is_in_metres(self):
        h = self.doc.header
        self.assertEqual((h["$INSUNITS"], h["$MEASUREMENT"], h["$LUNITS"]), (6, 1, 2))
        self.assertAlmostEqual(h["$TEXTSIZE"], 2.5 * self.drawing.scale / 1000.0)

    def test_the_sheet_starts_at_the_origin_and_the_header_says_how_far_it_reaches(self):
        h = self.doc.header
        lo, hi = h["$EXTMIN"], h["$EXTMAX"]
        self.assertGreaterEqual(min(lo[0], lo[1]), -1e-6)
        self.assertGreater(hi[0], 1.0)
        self.assertLess(hi[0], 1e6)
        W, H = self.drawing.size
        self.assertLessEqual(hi[0], W * self.drawing.scale / 1000.0 + 1e-3)
        self.assertLessEqual(hi[1], H * self.drawing.scale / 1000.0 + 1e-3)


if __name__ == "__main__":
    unittest.main()
