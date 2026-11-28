import unittest

from epc_report.core import numbers


class TestNumbers(unittest.TestCase):
    def test_long_decimals_are_rounded_and_thousands_grouped_per_language(self):
        self.assertEqual(numbers.text("E = 47983.544 kWh/year", "en"), "E = 47,983.54 kWh/year")
        self.assertEqual(numbers.text("E = 47983.544 kWh/año", "es"), "E = 47.983,54 kWh/año")
        self.assertEqual(numbers.text("R = 1.2", "es"), "R = 1,2")

    def test_negative_zero_and_scientific_notation_are_written_plainly(self):
        self.assertNotIn("e+", numbers.text("x = 1.1e+18 W", "en"))

    def test_a_single_string_is_singular(self):
        from epc_report.pv.texts import string_word
        self.assertEqual((string_word(1), string_word(2)), ("string", "strings"))

    def test_codes_versions_and_dates_stay_as_written(self):
        for s in ("SIM02-PV TR-001 C-05", "v0.1.0", "2026-11-27", "PV-10"):
            self.assertEqual(numbers.text(s, "es"), s)

    def test_a_range_is_written_number_by_number(self):
        self.assertEqual(numbers.text("tilt 0.0-90.0 deg", "es"), "tilt 0,0-90,0 deg")

    def test_a_report_keeps_its_facts_and_figures(self):
        rep = {"title": "T 1.23456", "blocks": [{"type": "p", "text": "x 2.5551"}, {"type": "figure", "path": "a1.234567.png"}], "facts": {"pv.ac_kwh": 47983.544}}
        out = numbers.localize(rep, "es")
        self.assertEqual((out["title"], out["blocks"][0]["text"], out["blocks"][1]["path"], out["facts"]), ("T 1,23", "x 2,56", "a1.234567.png", {"pv.ac_kwh": 47983.544}))
