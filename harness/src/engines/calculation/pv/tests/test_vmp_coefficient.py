"""The temperature coefficient of the maximum-power voltage: the data sheet value when the module gives it, else the open-circuit one with a warning."""
import unittest

from epc_pv import run, strings

from test_pv import INVERTER, MODULE, doc


class TestVmpCoefficient(unittest.TestCase):
    def test_a_much_stronger_coefficient_needs_more_modules_in_series_when_hot(self):
        same = strings.series_range(MODULE, INVERTER, -5.0, 70.0)
        own = strings.series_range(dict(MODULE, beta_vmp_pct_c=-1.5), INVERTER, -5.0, 70.0)      # exaggerated on purpose: the mechanics, not a module
        self.assertGreater(own["s_min"], same["s_min"])

    def test_without_it_the_open_circuit_one_is_used(self):
        self.assertEqual(strings.series_range(dict(MODULE, beta_vmp_pct_c=MODULE["beta_voc_pct_c"]), INVERTER, -5.0, 70.0), strings.series_range(MODULE, INVERTER, -5.0, 70.0))

    def test_the_warning_goes_only_when_a_module_lacks_it(self):
        codes = lambda r: [w["code"] for w in r.as_dict()["warnings"]]
        self.assertIn("wind_proxy", codes(run(doc())))
        given = doc(module=dict(MODULE, beta_vmp_pct_c=-0.30))
        self.assertNotIn("wind_proxy", codes(run(given)))


if __name__ == "__main__":
    unittest.main()
