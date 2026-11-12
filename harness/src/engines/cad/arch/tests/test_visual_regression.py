"""The PNG and the PDF of one drawing look the same: their structural similarity, with the PDF rasterized by the same library that reads PDFs, is at least 0.98 (PRD `visual_ssim`)."""
import io
import sys
import unittest
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from epc_arch import Options, recognize                          # noqa: E402
from epc_arch.drawing import build_drawing                        # noqa: E402
from epc_arch.export.compare import ssim                          # noqa: E402
from epc_arch.export.export_raster import to_pdf, to_png          # noqa: E402
import helpers                                                    # noqa: E402

DPI = 100


class TestVisualRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        arch = recognize(helpers.room_dxf(), "flat.dxf", Options()).architecture
        cls.drawing = build_drawing(arch, sheet="A3")

    def test_png_and_pdf_look_the_same(self):
        png = Image.open(io.BytesIO(to_png(self.drawing, dpi=DPI)))
        pdf = pdfium.PdfDocument(to_pdf(self.drawing))[0].render(scale=DPI / 72).to_pil()
        self.assertGreaterEqual(ssim(png, pdf), 0.98)

    def test_a_blank_sheet_does_not(self):
        a = Image.open(io.BytesIO(to_png(self.drawing, dpi=DPI)))
        self.assertLess(ssim(a, Image.new("L", a.size, 255)), 0.98)

    def test_the_same_picture_is_one(self):
        a = Image.open(io.BytesIO(to_png(self.drawing, dpi=DPI)))
        self.assertAlmostEqual(ssim(a, a), 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
