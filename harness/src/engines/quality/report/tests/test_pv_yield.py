"""The PV yield study as a report (ADR-0043): built from the result of `epc_pv` alone, nothing is read, and the same data give the same blocks and the same PDF bytes."""
import copy
import datetime
import unittest

from epc_report.core import report_docx, report_pdf
from epc_report.pv import yield_study

ARRAY = {"id": "A1", "modules": 20, "inverters": 1, "dc_kwp": 11.0, "ac_kw": 10.0, "dc_ac_ratio": 1.1, "strings": {"n_series": 10, "strings": 2, "strings_per_inverter": 2},
         "poa_kwh_m2": 1800.0, "ac_kwh": 15000.0, "specific_yield_kwh_kwp": 1363.6, "performance_ratio": 0.8, "capacity_factor": 0.17}
RESULT = {"arrays": [ARRAY], "counts": {"arrays": 1, "inverters": 1, "modules": 20, "hours": 8760}, "warnings": [{"en": "Typical weather", "es": "Clima típico"}],
          "totals": {"dc_kwp": 11.0, "ac_kw": 10.0, "ac_kwh": 15000.0, "specific_yield_kwh_kwp": 1363.6, "clipping_kwh": 12.0, "monthly_ac_kwh": [1000.0 + 10 * m for m in range(12)]}}
DOCUMENT = {"engine": {"name": "epc_pv", "version": "1"}, "result": RESULT}


class TestPvYield(unittest.TestCase):
    def test_the_report_has_the_tables_of_the_study(self):
        report = yield_study.pv_yield_report(DOCUMENT, "P-1")
        self.assertEqual((report["title"], report["subtitle"]), ("PV yield study", "P-1"))
        texts = [b.get("text") for b in report["blocks"] if b["type"] == "h"]
        self.assertIn("Monthly AC energy (kWh)", texts)
        self.assertIn("Equipment of the plant", texts)
        self.assertEqual(len([b for b in report["blocks"] if b["type"] == "table"]), 4)
        self.assertEqual(report["blocks"][-1]["items"], ["Typical weather / Clima típico"])

    def test_the_weight_is_a_line_only_when_the_caller_gives_it(self):
        text = lambda r: " ".join(b.get("text", "") for b in r["blocks"])      # noqa: E731
        self.assertNotIn("Module weight", text(yield_study.pv_yield_report(DOCUMENT, "P-1")))
        self.assertIn("Module weight (record of the module format): 25 kg each, 0.5 t in total", text(yield_study.pv_yield_report(DOCUMENT, "P-1", module_weight_kg=25.0)))

    def test_the_input_is_not_changed(self):
        before = copy.deepcopy(DOCUMENT)
        yield_study.pv_yield_report(DOCUMENT, "P-1", module_weight_kg=25.0)
        self.assertEqual(DOCUMENT, before)

    def test_the_same_data_give_the_same_files(self):
        date = datetime.datetime(2026, 11, 26)
        report = yield_study.pv_yield_report(DOCUMENT, "P-1")
        self.assertEqual(report_pdf.render_bytes(report, date=date), report_pdf.render_bytes(yield_study.pv_yield_report(DOCUMENT, "P-1"), date=date))
        self.assertEqual(report_docx.render_bytes(report, date=date), report_docx.render_bytes(yield_study.pv_yield_report(DOCUMENT, "P-1"), date=date))


if __name__ == "__main__":
    unittest.main()
