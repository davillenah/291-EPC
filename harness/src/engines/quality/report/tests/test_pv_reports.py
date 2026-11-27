"""The PV calculation memorandum and the summary (ADR-0043): nothing is calculated, English and Spanish, same data same bytes, and the audit finds nothing."""
import copy
import datetime
import unittest

from epc_report.errors import ReportError
from epc_report.core import audit, report_docx, report_pdf
from epc_report.pv import calc_memo, summary

ARRAY = {"id": "A1", "modules": 20, "inverters": 1, "dc_kwp": 11.0, "ac_kw": 10.0, "inverter_ac_kw": 10.0, "dc_ac_ratio": 1.1,
         "strings": {"n_series": 10, "series_range": {"s_min": 5, "s_max": 20}, "strings": 2, "strings_per_inverter": 2, "strings_per_mppt": 1, "strings_per_mppt_limit": 2},
         "poa_kwh_m2": 1800.0, "ac_kwh": 15000.0, "specific_yield_kwh_kwp": 1363.6, "performance_ratio": 0.8, "capacity_factor": 0.17}
RESULT = {"arrays": [ARRAY], "warnings": [{"en": "Typical weather", "es": "Clima típico"}],
          "totals": {"dc_kwp": 11.0, "ac_kw": 10.0, "ac_kwh": 15000.0, "specific_yield_kwh_kwp": 1363.6}}
DOCUMENT = {"engine": {"name": "epc_pv", "version": "1"}, "result": RESULT}
INPUTS = {"site": {"latitude_deg": -34.6, "longitude_deg": -58.4, "design_t_min_c": -5},
          "arrays": [{"id": "A1", "module": {"pmax_w": 550.0, "voc_v": 49.9, "vmp_v": 41.8, "beta_voc_pct_c": -0.27}, "inverter": {"vdc_max_v": 1100.0, "mppt_v_min": 200.0, "mppt_v_max": 1000.0}}]}


def texts(report):
    return " ".join(str(b.get("text", "")) + " ".join(str(c) for r in b.get("rows", []) for c in r) for b in report["blocks"])


class TestPvReports(unittest.TestCase):
    def test_memo_in_both_languages(self):
        en, es = calc_memo.pv_calc_memo(DOCUMENT, INPUTS, "P-1", "en"), calc_memo.pv_calc_memo(DOCUMENT, INPUTS, "P-1", "es")
        self.assertEqual((en["title"], es["title"]), ("PV calculation memorandum", "Memoria de cálculo fotovoltaica"))
        self.assertIn("complies", texts(en))
        self.assertIn("cumple", texts(es))
        self.assertIn("N_s,min = 5; N_s,max = 20; N_s = 10", texts(en))

    def test_a_failing_check_says_so(self):
        bad = copy.deepcopy(DOCUMENT)
        bad["result"]["arrays"][0]["strings"]["strings_per_mppt"] = 3
        self.assertIn("does not comply", texts(calc_memo.pv_calc_memo(bad, INPUTS, "P-1")))
        self.assertEqual(calc_memo.count_states("en", bad["result"]["arrays"]), [1, 1, 1])

    def test_summary_is_a_table_with_at_most_three_observations(self):
        many = copy.deepcopy(DOCUMENT)
        many["result"]["warnings"] = [{"en": f"w{i}", "es": f"a{i}"} for i in range(6)]
        rep = summary.pv_summary(many, INPUTS, "P-1", "consumption 20000 kWh/year")
        self.assertEqual(len(rep["blocks"][-1]["items"]), 3)
        self.assertIn("not available", texts(rep))
        self.assertIn("Planta FV 11,0 kWp CC / 10,0 kW CA", texts(summary.pv_summary(DOCUMENT, INPUTS, "P-1", "x", "es")))

    def test_the_audit_finds_nothing_and_the_facts_agree(self):
        reports = [calc_memo.pv_calc_memo(DOCUMENT, INPUTS, "P-1"), summary.pv_summary(DOCUMENT, INPUTS, "P-1", "x")]
        self.assertEqual([f for f in audit.audit(reports) if f["severity"] == "error"], [])
        self.assertEqual(reports[0]["facts"], reports[1]["facts"])

    def test_the_inputs_are_not_changed_and_the_bytes_repeat(self):
        before = (copy.deepcopy(DOCUMENT), copy.deepcopy(INPUTS))
        date = datetime.datetime(2026, 11, 27)
        rep = calc_memo.pv_calc_memo(DOCUMENT, INPUTS, "P-1")
        self.assertEqual((DOCUMENT, INPUTS), before)
        self.assertEqual(report_pdf.render_bytes(rep, date=date), report_pdf.render_bytes(calc_memo.pv_calc_memo(DOCUMENT, INPUTS, "P-1"), date=date))
        self.assertEqual(report_docx.render_bytes(rep, date=date), report_docx.render_bytes(calc_memo.pv_calc_memo(DOCUMENT, INPUTS, "P-1"), date=date))

    def test_a_template_that_is_not_a_block_reads_as_not_available(self):
        inputs = {"site": INPUTS["site"], "arrays": [{"id": "A1", "module": "auto", "inverter": "auto"}]}
        self.assertIn("not available", texts(calc_memo.pv_calc_memo(DOCUMENT, inputs, "P-1")))
        self.assertIn("not available", texts(summary.pv_summary(DOCUMENT, inputs, "P-1", "x")))

    def test_unknown_language_is_an_error(self):
        with self.assertRaises(ReportError) as ctx:
            calc_memo.pv_calc_memo(DOCUMENT, INPUTS, "P-1", "fr")
        self.assertEqual((ctx.exception.code, ctx.exception.es), ("err_language_unknown", "el idioma debe ser uno de en, es, no fr"))


if __name__ == "__main__":
    unittest.main()


class TestPvEconomicReports(unittest.TestCase):
    ECO = {"energy_kwh_year": 15000.0, "energy_price": 0.1, "currency": "USD", "saving_year": 1500.0, "saving_month": [125.0] * 12, "investment": 9000.0, "simple_payback_years": 6.0,
           "assumes": {"en": "all the energy is used on site", "es": "toda la energía se usa en el sitio"}}

    def doc(self, eco=None):
        d = copy.deepcopy(DOCUMENT)
        d["result"]["totals"]["monthly_ac_kwh"] = [1000.0] * 12
        if eco is not None:
            d["result"]["technical_feasibility"] = {"economic": eco}
        return d

    def test_savings_and_economic_memos_are_two_documents_that_agree(self):
        from epc_report.pv import economics
        d = self.doc(self.ECO)
        sav, eco = economics.pv_savings_memo(d, "P-1"), economics.pv_economic_memo(d, "P-1", "es")
        self.assertNotEqual(sav["title"], eco["title"])
        self.assertIn("A = 15,000.0 kWh × 0.1 USD/kWh", texts(sav))
        self.assertIn("T = 6,0", texts(eco))
        self.assertEqual(sav["facts"]["pv.saving_year"], eco["facts"]["pv.saving_year"])
        self.assertEqual([f for f in audit.audit([sav, eco]) if f["severity"] == "error"], [])

    def test_what_the_client_did_not_give_is_not_verified_never_assumed(self):
        from epc_report.pv import economics
        self.assertIn("price is not given", texts(economics.pv_savings_memo(self.doc(), "P-1")))
        no_invest = dict(self.ECO)
        del no_invest["investment"]
        self.assertIn("investment is not given", texts(economics.pv_economic_memo(self.doc(no_invest), "P-1")))

    def test_the_descriptive_reports_are_narrative_in_both_languages(self):
        from epc_report.pv import narrative
        d = self.doc(self.ECO)
        for fn in (narrative.pv_descriptive_report, narrative.pv_savings_descriptive, narrative.pv_economic_descriptive):
            en, es = fn(d, "P-1", "consumption", "en"), fn(d, "P-1", "consumo", "es")
            self.assertNotEqual(en["title"], es["title"])
            self.assertEqual([f for f in audit.audit([en, es]) if f["severity"] == "error"], [])
        self.assertIn("simple payback of 6.0 years", texts(narrative.pv_economic_descriptive(d, "P-1", "x")))
        self.assertIn("not calculated", texts(narrative.pv_savings_descriptive(self.doc(), "P-1", "x")))
