"""The cover page of a report: it is page 1, carries the data of the document and a logo when it can be read; the text starts on page 2."""
import json
import tempfile
import unittest
from pathlib import Path

from epc_drawing.export import report_pdf


def _png(path: Path) -> None:
    from PIL import Image
    Image.new("RGB", (200, 80), (200, 30, 30)).save(path)


class TestCover(unittest.TestCase):
    REPORT = {"title": "Estudio de cortocircuito", "subtitle": "P-1-ELE-005", "footer": "Demo", "page_label": "Página {n} de {total}",
              "blocks": [{"type": "p", "text": "Texto del estudio."}]}

    def test_the_cover_is_the_first_page_and_the_text_starts_on_the_second(self):
        import pypdfium2 as pdfium
        with tempfile.TemporaryDirectory() as d:
            logo, dst = Path(d) / "logo.png", Path(d) / "r.pdf"
            _png(logo)
            rep = {**self.REPORT, "cover": {"logos": [str(logo), None], "rows": [["Proyecto", "Demo"], ["Revisión", "Rev 00"]]}}
            report_pdf.render(rep, dst)
            pdf = pdfium.PdfDocument(str(dst))
            self.assertEqual(len(pdf), 2)
            first, second = (pdf[i].get_textpage().get_text_range() for i in (0, 1))
            self.assertIn("Rev 00", first)
            self.assertIn("Estudio de cortocircuito", first)
            self.assertNotIn("Texto del estudio.", first)
            self.assertIn("Texto del estudio.", second)
            self.assertIn("Página 2 de 2", second)
            img = pdf[0].render(scale=0.5).to_pil().convert("RGB")
            self.assertTrue(any(img.getpixel((x, y))[0] > 180 and img.getpixel((x, y))[1] < 80 for x in range(0, img.width, 4) for y in range(0, 90, 4)))      # the red logo is on the page
            pdf.close()                                                          # Windows does not remove a folder with an open file

    def test_without_a_cover_nothing_changes_and_an_unreadable_logo_is_left_out(self):
        import pypdfium2 as pdfium
        with tempfile.TemporaryDirectory() as d:
            plain, bad = Path(d) / "a.pdf", Path(d) / "b.pdf"
            report_pdf.render(self.REPORT, plain)
            one = pdfium.PdfDocument(str(plain))
            self.assertEqual(len(one), 1)
            one.close()
            broken = Path(d) / "broken.png"
            broken.write_bytes(b"not an image")
            report_pdf.render({**self.REPORT, "cover": {"logos": [str(broken)], "rows": []}}, bad)
            two = pdfium.PdfDocument(str(bad))
            self.assertEqual(len(two), 2)
            two.close()


if __name__ == "__main__":
    unittest.main()
