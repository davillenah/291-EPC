"""A logo for the covers: PNG and JPEG as they are, an SVG drawn here (filled shapes with their colours, holes, strokes), and nothing (not an error) when the file cannot be read."""
import tempfile
import unittest
import zipfile
from pathlib import Path

from epc_report.core import logo, report_docx, report_pdf

SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50" width="100" height="50">
<rect x="0" y="0" width="100" height="50" fill="#ff0000"/>
<path d="M20 10 L80 10 L80 40 L20 40 Z M35 20 L65 20 L65 30 L35 30 Z" fill="#0000ff"/>
<circle cx="50" cy="25" r="3" fill="none" stroke="#00ff00" stroke-width="2"/>
</svg>"""


def _write(d: Path, name: str, text: str) -> Path:
    p = d / name
    p.write_text(text, encoding="utf-8")
    return p


class TestLogo(unittest.TestCase):
    def test_an_svg_is_drawn_with_its_colours_and_its_holes(self):
        with tempfile.TemporaryDirectory() as d:
            im = logo.image(_write(Path(d), "l.svg", SVG))
            self.assertEqual(im.mode, "RGBA")
            self.assertAlmostEqual(im.width / im.height, 2.0, delta=0.05)                          # the proportions of the drawing
            w, h = im.size
            at = lambda fx, fy: im.getpixel((int(w * fx), int(h * fy)))[:3]
            self.assertEqual(at(0.05, 0.05), (255, 0, 0))                                         # the red background
            self.assertEqual(at(0.25, 0.5), (0, 0, 255))                                          # the blue frame
            self.assertEqual(at(0.42, 0.5), (255, 0, 0))                                          # its hole shows the red behind (even-odd)

    def test_png_is_opened_and_what_is_not_an_image_gives_nothing(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            png = Path(d) / "a.png"
            Image.new("RGB", (30, 10), (9, 9, 9)).save(png)
            self.assertEqual(logo.image(png).size, (30, 10))
            self.assertIsNone(logo.image(_write(Path(d), "b.png", "not an image")))
            self.assertIsNone(logo.image(_write(Path(d), "c.svg", "<svg")))
            self.assertIsNone(logo.image(_write(Path(d), "d.txt", "x")))
            self.assertIsNone(logo.image(Path(d) / "missing.png"))
            self.assertIsNone(logo.image(None))

    def test_the_covers_carry_an_svg_logo(self):
        import pypdfium2 as pdfium
        rep = {"title": "T", "subtitle": "S", "footer": "f", "page_label": "{n}/{total}", "blocks": [{"type": "p", "text": "x"}]}
        with tempfile.TemporaryDirectory() as d:
            svg = _write(Path(d), "l.svg", SVG)
            report_pdf.render({**rep, "cover": {"logos": [str(svg)], "rows": []}}, Path(d) / "r.pdf")
            pdf = pdfium.PdfDocument(str(Path(d) / "r.pdf"))
            img = pdf[0].render(scale=0.5).to_pil().convert("RGB")
            self.assertTrue(any(img.getpixel((x, y))[0] > 200 and img.getpixel((x, y))[2] < 60 for x in range(0, img.width, 3) for y in range(0, 90, 3)))      # the red of the logo is on the page
            pdf.close()
            report_docx.render({**rep, "cover": {"logos": [str(svg)], "rows": []}}, Path(d) / "r.docx")
            with zipfile.ZipFile(Path(d) / "r.docx") as z:
                self.assertTrue(any(n.startswith("word/media/") and n.endswith(".png") for n in z.namelist()))                                   # carried as a PNG


if __name__ == "__main__":
    unittest.main()
