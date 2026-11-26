"""The Word version of a structured report: a valid package (every part is well-formed XML), the text of the report in it, a cover with its logo and the footer fields."""
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from epc_report.core import report_docx

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
REPORT = {"title": "Estudio de cortocircuito", "subtitle": "P-1-ELE-005", "footer": "Demo · P-1", "page_label": "Página {n} de {total}",
          "blocks": [{"type": "kv", "rows": [["Proyecto", "Demo"]]}, {"type": "h", "text": "Resumen"}, {"type": "p", "text": "Texto <con> & símbolos."},
                     {"type": "bullets", "items": ["uno", "dos"]}, {"type": "table", "columns": [["Tablero", 0.4], ["Estado", 0.6]], "rows": [["TGBT", "Cumple"], ["TS-1", "Revisar"]], "empty": "Sin datos"}]}


def _texts(z: zipfile.ZipFile, part: str) -> list:
    return ["".join(t.text or "" for t in p.iter(W + "t")) for p in ET.fromstring(z.read(part)).iter(W + "p")]


class TestReportDocx(unittest.TestCase):
    def test_the_package_is_well_formed_and_has_the_text_of_the_report(self):
        with tempfile.TemporaryDirectory() as d:
            dst = Path(d) / "r.docx"
            report_docx.render(REPORT, dst)
            with zipfile.ZipFile(dst) as z:
                self.assertIsNone(z.testzip())
                for name in z.namelist():
                    ET.fromstring(z.read(name))                                              # every part parses
                text = _texts(z, "word/document.xml")
                self.assertIn("Estudio de cortocircuito", text)
                self.assertIn("Texto <con> & símbolos.", text)                              # reserved characters come back as they were
                self.assertTrue(any(t.startswith("•  uno") for t in text))
                self.assertIn("Cumple", text)
                doc = z.read("word/document.xml").decode("utf-8")
                self.assertIn('w:val="Heading1"', doc)
                self.assertIn("<w:tblHeader/>", doc)                                         # the header row of a table repeats on each page
                self.assertIn("NUMPAGES", z.read("word/footer1.xml").decode("utf-8"))

    def test_a_cover_has_its_logo_its_data_and_a_page_break(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            logo, dst = Path(d) / "logo.png", Path(d) / "r.docx"
            Image.new("RGB", (200, 80), (200, 30, 30)).save(logo)
            report_docx.render({**REPORT, "cover": {"logos": [str(logo), None, ], "rows": [["Revisión", "Rev 00"]]}}, dst)
            with zipfile.ZipFile(dst) as z:
                names = z.namelist()
                self.assertTrue(any(n.startswith("word/media/") for n in names))
                self.assertIn("rIdImg1", z.read("word/_rels/document.xml.rels").decode("utf-8"))
                self.assertIn('w:type="page"', z.read("word/document.xml").decode("utf-8"))
                self.assertIn("Rev 00", _texts(z, "word/document.xml"))
            broken = Path(d) / "broken.png"
            broken.write_bytes(b"not an image")
            report_docx.render({**REPORT, "cover": {"logos": [str(broken)], "rows": []}}, Path(d) / "b.docx")      # a logo that cannot be read is left out
            with zipfile.ZipFile(Path(d) / "b.docx") as z:
                self.assertFalse(any(n.startswith("word/media/") for n in z.namelist()))

    def test_the_command_line_writes_the_file(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d) / "r.json", Path(d) / "out" / "r.docx"
            src.write_text(json.dumps(REPORT), encoding="utf-8")
            self.assertEqual(report_docx.main([str(src), str(dst)]), 0)
            self.assertTrue(dst.is_file())
            self.assertEqual(report_docx.main([]), 2)


if __name__ == "__main__":
    unittest.main()
