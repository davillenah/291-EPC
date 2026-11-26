"""The four exports of one drawing are sound and agree: same layers in SVG and DXF, a DXF that audits clean in metres, a vector PDF, a PNG at the dpi asked."""
import io
import re
import sys
import unittest
import zlib
from pathlib import Path

import ezdxf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from epc_draw.arch import Options, recognize                          # noqa: E402
from epc_draw.arch.drawing import build_drawing                        # noqa: E402
from epc_draw.arch.export.export_dxf import to_dxf                     # noqa: E402
from epc_draw.arch.export.export_raster import to_pdf, to_png          # noqa: E402
from epc_draw.arch.export.export_svg import to_svg                     # noqa: E402
import arch_helpers as helpers                                                    # noqa: E402


class TestExportIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.arch = recognize(helpers.room_dxf(), "flat.dxf", Options()).architecture
        cls.drawing = build_drawing(cls.arch, sheet="A3")
        cls.svg, cls.dxf = to_svg(cls.drawing), to_dxf(cls.drawing)

    def test_the_dxf_audits_clean_and_is_in_metres(self):
        doc = ezdxf.read(io.StringIO(self.dxf))
        self.assertEqual(len(doc.audit().errors), 0)
        self.assertEqual(doc.units, 6)
        self.assertAlmostEqual(doc.header["$LTSCALE"], self.drawing.scale / 1000.0)

    def test_svg_and_dxf_have_the_same_layers(self):
        in_svg = set(re.findall(r'<g id="(291-[A-Z0-9-]+|0-[A-Za-z]+)"', self.svg))
        doc = ezdxf.read(io.StringIO(self.dxf))
        used = {e.dxf.layer for e in doc.modelspace()}
        used |= {e.dxf.layer for ins in doc.modelspace().query("INSERT") for e in doc.blocks.get(ins.dxf.name)}        # doors and windows are blocks: their lines are in the block
        self.assertEqual(in_svg, used | {h.dxf.layer for h in doc.entitydb.values() if h.dxftype() == "HATCH"})

    def test_layers_of_the_dxf_carry_the_style(self):
        doc = ezdxf.read(io.StringIO(self.dxf))
        self.assertEqual(doc.layers.get("291-A-WALL-FULL-N").dxf.lineweight, 50)
        self.assertEqual(doc.layers.get("291-A-DOOR-FULL-N").dxf.linetype, "DASHED")

    def test_the_svg_is_in_paper_millimetres(self):
        self.assertIn('width="420mm" height="297mm"', self.svg)
        self.assertIn('stroke-width="0.5"', self.svg)

    def test_the_pdf_is_vector_with_arial(self):
        pdf = to_pdf(self.drawing)
        self.assertTrue(pdf.startswith(b"%PDF-"))
        body = zlib.decompress(re.search(rb"stream\n(.*?)\nendstream", pdf, re.S).group(1))
        self.assertIn(b" l ", body)
        self.assertIn(b"Tj", body)
        self.assertIn(b"/BaseFont /ArialMT", pdf)                                   # Arial, named and not embedded

    def test_the_png_has_the_size_of_the_sheet_at_the_dpi(self):
        from PIL import Image
        im = Image.open(io.BytesIO(to_png(self.drawing, dpi=50)))
        self.assertEqual(im.size, (round(420 * 50 / 25.4), round(297 * 50 / 25.4)))


if __name__ == "__main__":
    unittest.main()
