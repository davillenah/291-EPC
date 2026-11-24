"""The sheet of a drawing can be an IRAM sheet SVG (as `epc_titleblock` makes it): its frame, coordinates and title block become marks of the drawing in the four formats, the plan goes in the zone
that the sheet leaves free, and the fields of the title block take the scale and the name of the plan. The sheet is given as SVG text: the engines do not import one another."""
import base64
import io
import sys
import unittest
import zlib
from pathlib import Path

import ezdxf
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from epc_arch import Options, recognize                          # noqa: E402
from epc_arch.drawing import ImageItem, Poly, TextItem, build_drawing   # noqa: E402
from epc_arch.export.export_dxf import to_dxf                     # noqa: E402
from epc_arch.export.export_raster import to_pdf, to_png          # noqa: E402
from epc_arch.export.export_svg import to_svg                     # noqa: E402
from epc_arch.export.sheet_iram import load_template              # noqa: E402
from epc_arch.model import ArchError                              # noqa: E402
import helpers                                                    # noqa: E402


def _logo() -> str:
    buf = io.BytesIO()
    Image.new("RGBA", (40, 20), (200, 30, 30, 255)).save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


SHEET = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="420mm" height="297mm" viewBox="0 0 420 297" data-format="A3" data-zona-util="30 15 405 282" data-rotulo="230 231 405 282" data-modificaciones="230 209.5 405 231">
<rect id="papel" x="0" y="0" width="420" height="297" fill="#fff"/>
<g id="recuadro" stroke="#000"><rect x="25" y="10" width="385" height="277" fill="none" stroke-width="1.0"/></g>
<g id="coordenadas" stroke="#000" fill="#000"><text stroke="none" x="69.25" y="284.5" font-size="4.861" text-anchor="middle" transform="rotate(-90 69.25 284.5)">D</text></g>
<g id="rotulo" transform="translate(230 231)" stroke="#000"><rect x="0" y="0" width="175" height="51" fill="none" stroke-width="0.8"/>
<text stroke="none" x="12.4" y="32.5" font-size="2.778" text-anchor="middle" data-key="escala" data-placeholder="S/E">S/E</text>
<text stroke="none" x="100" y="32.5" font-size="2.778" text-anchor="middle" data-key="denominacion" data-placeholder="{{denominacion}}">{{denominacion}}</text>
<text stroke="none" x="100" y="40" font-size="2.778" text-anchor="middle" data-key="proyecto">{{proyecto}}</text>
<g id="logo" transform="translate(66 1)"><image x="0" y="0" width="20" height="10" xlink:href="data:image/png;base64,{_logo()}"/></g></g>
<g id="dibujo"><!-- the drawing goes here --></g></svg>"""


class TestSheetTemplate(unittest.TestCase):
    def test_the_sheet_says_its_name_size_and_the_zone_it_leaves_free(self):
        t = load_template(SHEET)
        self.assertEqual((t.name, t.size), ("A3", (420.0, 297.0)))
        self.assertEqual(t.free, (35.0, 20.0, 400.0, 204.5))                 # the usable zone above the list of modifications, with a clear gap

    def test_a_sheet_that_is_not_an_iram_sheet_is_refused(self):
        with self.assertRaises(ArchError):
            load_template('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="5" height="5" stroke="#000"/></svg>')
        with self.assertRaises(ArchError):
            load_template("<svg")

    def test_its_marks_keep_their_widths_sizes_turns_and_pictures(self):
        t = load_template(SHEET)
        widths = sorted({i.width for i in t.items if isinstance(i, Poly)})
        self.assertEqual(widths, [0.8, 1.0])
        turned = [i for i in t.items if isinstance(i, TextItem) and i.value == "D"][0]
        self.assertEqual((turned.rotation, turned.size, turned.anchor), (-90.0, 4.861, "middle"))
        logo = [i for i in t.items if isinstance(i, ImageItem)][0]
        self.assertEqual((round(logo.x), round(logo.y), round(logo.w), round(logo.h)), (296, 232, 20, 10))     # at the translate of the title block and of the logo

    def test_the_paper_of_the_sheet_is_not_a_mark(self):
        t = load_template(SHEET)
        self.assertFalse([i for i in t.items if isinstance(i, Poly) and i.fill and i.width is None and len(i.points) == 4 and i.points[2] == (420.0, 297.0)])

    def test_the_fields_take_values_and_an_empty_one_stays_blank(self):
        t = load_template(SHEET)
        values = {i.value for i in t.filled({"escala": "1:100"}) if isinstance(i, TextItem)}
        self.assertIn("1:100", values)
        self.assertNotIn("{proyecto}", values)                                # nobody gave it: blank, not the key
        self.assertIn("Casa", {i.value for i in t.filled({"proyecto": "Casa"}) if isinstance(i, TextItem)})


class TestDrawingOnAnIramSheet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.arch = recognize(helpers.room_dxf(), "flat.dxf", Options()).architecture
        cls.drawing = build_drawing(cls.arch, template=load_template(SHEET), fields={"proyecto": "Casa de prueba"})

    def test_the_sheet_is_the_iram_one_and_the_plan_is_in_its_free_area(self):
        d = self.drawing
        self.assertEqual((d.sheet, d.size, d.template), ("A3", (420.0, 297.0), "A3"))
        walls = [i for i in d.of("291-A-WALL-FULL-N") if isinstance(i, Poly)]
        xs = [p[0] for w in walls for p in w.points]
        ys = [p[1] for w in walls for p in w.points]
        self.assertTrue(35.0 <= min(xs) and max(xs) <= 400.0 and 20.0 <= min(ys) and max(ys) <= 204.5)

    def test_the_title_block_has_the_scale_the_plan_is_drawn_at_and_the_given_fields(self):
        texts = {i.value for i in self.drawing.of("0-Titleblock") if isinstance(i, TextItem)}
        self.assertTrue({f"1:{self.drawing.scale}", "Casa de prueba"} <= texts)
        self.assertIn(self.drawing.title, texts)                              # the sheet had only the `{denominacion}` sample: the plan's name goes there

    def test_every_format_shows_the_sheet(self):
        d = self.drawing
        svg = to_svg(d)
        self.assertIn('stroke-width="1"', svg)
        self.assertIn("<image ", svg)
        self.assertIn('transform="rotate(-90 69.25 284.5)"', svg)
        doc = ezdxf.read(io.StringIO(to_dxf(d)))
        self.assertEqual(len(doc.audit().errors), 0)
        self.assertTrue([e for e in doc.modelspace() if e.dxftype() == "TEXT" and abs(e.dxf.rotation - 90.0) < 1e-6])
        pdf = to_pdf(d)
        self.assertIn(b"/Subtype /Image", pdf)
        body = zlib.decompress(__import__("re").search(rb"stream\n(.*?)\nendstream", pdf, __import__("re").S).group(1))
        self.assertIn(b" Do Q", body)
        png = Image.open(io.BytesIO(to_png(d, dpi=50)))
        self.assertEqual(png.size, (round(420 * 50 / 25.4), round(297 * 50 / 25.4)))

    def test_a_logo_is_in_the_picture_of_the_sheet(self):
        png = Image.open(io.BytesIO(to_png(self.drawing, dpi=100))).convert("L")
        ppm = 100 / 25.4
        box = png.crop((int(296 * ppm), int(232 * ppm), int(316 * ppm), int(242 * ppm)))
        self.assertLess(box.getextrema()[0], 200)                              # the red logo is grey ink there, not blank paper


if __name__ == "__main__":
    unittest.main()
