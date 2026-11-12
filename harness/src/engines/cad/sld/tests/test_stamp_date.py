"""MIG-3Z: the single-line generator takes an optional drawing date (title block issue date and DXF stamps); without it, today's date."""
import datetime
import sys
import unittest
from pathlib import Path
from unittest import mock

ENGINES = Path(__file__).resolve().parents[3]                # harness/src/engines: one folder per group (cad, calculation, ...)
sys.path[:0] = [str(ENGINES / g / a / "src") for g, a in (("cad", "sld"), ("calculation", "aea90364"), ("cad", "symbols"), ("cad", "titleblock"), ("cad", "dxf"))]

from epc_sld import sld_generator as G   # noqa: E402


def bare_sheet(stamp_date):
    sheet = G._Sheet.__new__(G._Sheet)
    sheet.stamp_date = stamp_date
    return sheet


class TestIssueDate(unittest.TestCase):
    def test_the_given_date_is_the_issue_date(self):
        self.assertEqual(bare_sheet("2026-03-04").issue_date(), "04/03/2026")
        self.assertEqual(bare_sheet("2026-03-04T23:30:00").issue_date(), "04/03/2026")

    def test_without_a_date_it_is_today(self):
        self.assertEqual(bare_sheet(None).issue_date(), datetime.date.today().strftime("%d/%m/%Y"))


class TestGenerateOption(unittest.TestCase):
    def sheet_env(self, environ=None, **kw):
        with mock.patch.object(G, "_Sheet") as sheet:
            G.generate("lib", "x.xlsx", "out", "N", environ={"SLD_FORMATO": "A1"} if environ is None else environ, **kw)
        return sheet.call_args.args[-1]

    def test_the_option_reaches_the_sheet_through_its_environment(self):
        self.assertEqual(self.sheet_env(stamp_date="2026-03-04")["EPC_STAMP_DATE"], "2026-03-04")

    def test_the_environment_variable_alone_works_and_nothing_is_added_without_either(self):
        self.assertEqual(self.sheet_env({"EPC_STAMP_DATE": "2026-03-05"})["EPC_STAMP_DATE"], "2026-03-05")
        self.assertNotIn("EPC_STAMP_DATE", self.sheet_env())

    def test_the_caller_environment_is_not_modified(self):
        env = {"SLD_FORMATO": "A1"}
        self.sheet_env(env, stamp_date="2026-03-04")
        self.assertEqual(env, {"SLD_FORMATO": "A1"})


if __name__ == "__main__":
    unittest.main()
