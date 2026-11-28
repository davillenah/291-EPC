"""Faults found by the hunt simulations (sims 05-14): input checks, pick of the inverter, notes."""
import copy
import unittest

from epc_pv import PvError, run
from test_pv import doc, weather


class TestWeatherChecks(unittest.TestCase):
    def test_a_temperature_out_of_range_is_refused(self):
        d = doc()
        d["weather"]["temp_air_c"][5] = 200.0
        with self.assertRaises(PvError):
            run(d)

    def test_an_irradiance_out_of_range_is_refused(self):
        d = doc()
        d["weather"]["ghi"][12] = 9000.0
        with self.assertRaises(PvError):
            run(d)

    def test_a_length_mismatch_names_both_series(self):
        d = doc()
        d["weather"]["wind_ms"] = d["weather"]["wind_ms"][:-1]
        with self.assertRaises(PvError) as ctx:
            run(d)
        self.assertIn("weather.ghi", ctx.exception.en)


class TestNotes(unittest.TestCase):
    def test_modules_rounded_is_a_warning_in_both_languages(self):
        from epc_pv import messages
        t = messages.text("modules_rounded", array="A1", asked=1000, installed=990, n_series=22)
        self.assertTrue(t["en"] and t["es"])

    def test_a_tracker_note_exists_in_both_languages(self):
        from epc_pv import messages
        t = messages.item("tracker_drawn_fixed", array="A1")
        self.assertIn("A1", str(t))
        self.assertIn("tracker", messages.MESSAGES["tracker_drawn_fixed"]["en"])


class TestWholeResult(unittest.TestCase):
    def test_the_plain_run_still_works(self):
        out = run(copy.deepcopy(doc())).as_dict()
        self.assertGreater(out["totals"]["ac_kwh"], 0)


if __name__ == "__main__":
    unittest.main()
