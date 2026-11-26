"""The writers moved from `epc_drawing.export` into `epc_report.core` (ADR-0043): the old names are doors, the same module objects, so classes, settings and behaviour are shared."""
import importlib
import unittest

MOVED = ("report_pdf", "report_docx", "logo", "tables_xlsx", "transmittal_pdf")


class TestDoor(unittest.TestCase):
    def test_the_old_module_is_the_new_module(self):
        for name in MOVED:
            old = importlib.import_module(f"epc_drawing.export.{name}")
            new = importlib.import_module(f"epc_report.core.{name}")
            self.assertIs(old, new, name)

    def test_from_import_gives_the_new_module(self):
        importlib.import_module("epc_drawing.export.report_pdf")
        importlib.import_module("epc_report.core.report_pdf")
        self.assertIs(importlib.import_module("epc_drawing.export").report_pdf, importlib.import_module("epc_report.core").report_pdf)


if __name__ == "__main__":
    unittest.main()
