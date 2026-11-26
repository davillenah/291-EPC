"""Same input and the same clock give the same bytes, for the PDF and the Word writer (ADR-0043, same logic as the drawing engine's byte tests).

The writers still read the clock (PDF creation date, zip entry times); the clock is fixed here. Taking the clock out of the writers (the date travels as an argument) is the next step."""
import hashlib
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from epc_report.core import report_docx, report_pdf

REPORT = {"title": "Estudio de prueba", "subtitle": "P-1", "footer": "Demo", "page_label": "Página {n} de {total}",
          "blocks": [{"type": "h", "text": "Sección"}, {"type": "p", "text": "Texto del informe. " * 40},
                     {"type": "table", "columns": [["a", 0.3], ["b", 0.3], ["c", 0.4]], "rows": [[1, 2.5, "x"], [3, 4.5, "y"]]},
                     {"type": "bullets", "items": ["uno", "dos"]}]}


def _digest(render, suffix):
    with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "1700000000"}), mock.patch.object(time, "time", return_value=1700000000.0):
        dst = Path(d) / f"r{suffix}"
        render(REPORT, dst)
        return hashlib.sha256(dst.read_bytes()).hexdigest()


class TestBytes(unittest.TestCase):
    def test_pdf_is_reproducible(self):
        self.assertEqual(_digest(report_pdf.render, ".pdf"), _digest(report_pdf.render, ".pdf"))

    def test_docx_is_reproducible(self):
        self.assertEqual(_digest(report_docx.render, ".docx"), _digest(report_docx.render, ".docx"))


if __name__ == "__main__":
    unittest.main()


class TestCalledAsAFunction(unittest.TestCase):
    """ADR-0043: a report is called with all its data and answers bytes; with a date given the clock is not read."""
    DATE = __import__("datetime").datetime(2026, 11, 26, 12, 0, 0)

    @staticmethod
    def _png_bytes():
        import io
        from PIL import Image
        out = io.BytesIO()
        Image.new("RGB", (200, 80), (200, 30, 30)).save(out, format="PNG")
        return out.getvalue()

    def _report(self, logos):
        return {**REPORT, "cover": {"logos": logos, "rows": [["Proyecto", "Demo"]]}}

    def test_same_bytes_with_a_date_and_without_patching_the_clock(self):
        report = self._report([self._png_bytes(), None])
        for module in (report_pdf, report_docx):
            first, second = module.render_bytes(report, date=self.DATE), module.render_bytes(report, date=self.DATE)
            self.assertEqual(first, second, module.__name__)
            self.assertTrue(first)

    def test_a_logo_as_data_gives_the_same_report_as_the_file(self):
        with tempfile.TemporaryDirectory() as d:
            logo = Path(d) / "l.png"
            logo.write_bytes(self._png_bytes())
            for module in (report_pdf, report_docx):
                from_file = module.render_bytes(self._report([str(logo), None]), date=self.DATE)
                from_data = module.render_bytes(self._report([self._png_bytes(), None]), date=self.DATE)
                self.assertEqual(from_file, from_data, module.__name__)
                self.assertEqual(from_data, module.render_bytes(self._report([{"data": self._png_bytes()}, None]), date=self.DATE), module.__name__)

    def test_a_logo_as_svg_data_is_drawn_and_an_unreadable_one_is_left_out(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20"><rect width="40" height="20" fill="#1f4e8c"/></svg>'
        self.assertTrue(report_pdf.render_bytes(self._report([svg]), date=self.DATE).startswith(b"%PDF"))
        self.assertTrue(report_pdf.render_bytes(self._report([b"not an image"]), date=self.DATE).startswith(b"%PDF"))

    def test_render_writes_what_render_bytes_returns(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(time, "time", return_value=1700000000.0), mock.patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "1700000000"}):
            dst = Path(d) / "r.docx"
            report_docx.render(REPORT, dst)
            self.assertEqual(dst.read_bytes(), report_docx.render_bytes(REPORT))
