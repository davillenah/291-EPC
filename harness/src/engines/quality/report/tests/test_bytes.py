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
