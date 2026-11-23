"""OPT-13: invariants of the photovoltaic `run` over generated documents (seeded, standard library only).

The synthetic weather and the module and inverter data of `test_pv` are reused; the generated values are the array size, the tilt and the DC to AC ratio.
"""
import copy
import random
import unittest

from epc_pv import run
from test_pv import doc

SAMPLES = 12


def _array(rng):
    return {"n_modules": rng.randint(50, 2000), "tilt_deg": rng.uniform(0, 45), "azimuth_deg": rng.uniform(0, 360), "dc_ac_ratio": rng.uniform(1.0, 1.4)}


def _totals(document):
    return run(copy.deepcopy(document)).as_dict()["totals"]


class PvProperties(unittest.TestCase):
    def test_more_modules_never_lower_the_dc_power_nor_the_energy(self):
        rng = random.Random(41)
        for _ in range(SAMPLES):
            spec = _array(rng)
            more = dict(spec, n_modules=spec["n_modules"] * 2)
            small, big = _totals(doc(**spec)), _totals(doc(**more))
            with self.subTest(spec=spec):
                self.assertGreaterEqual(big["dc_kwp"], small["dc_kwp"])
                self.assertGreaterEqual(big["ac_kwh"], small["ac_kwh"] - 1e-6)

    def test_the_energy_is_never_negative_and_never_exceeds_the_dc_energy(self):
        rng = random.Random(42)
        for _ in range(SAMPLES):
            spec = _array(rng)
            totals = _totals(doc(**spec))
            with self.subTest(spec=spec):
                self.assertGreaterEqual(totals["ac_kwh"], 0)
                self.assertLessEqual(totals["ac_kwh"], totals["dc_kwh"] + 1e-6)
                self.assertGreaterEqual(totals["clipping_kwh"], 0)
                self.assertAlmostEqual(sum(totals["monthly_ac_kwh"]), totals["ac_kwh"], delta=0.05)

    def test_the_array_power_follows_the_module_count(self):
        rng = random.Random(43)
        for _ in range(SAMPLES):
            spec = _array(rng)
            out = run(copy.deepcopy(doc(**spec))).as_dict()
            with self.subTest(spec=spec):
                self.assertGreaterEqual(out["arrays"][0]["modules"], spec["n_modules"])
                self.assertAlmostEqual(out["totals"]["dc_kwp"], out["arrays"][0]["dc_kwp"], delta=0.01)

    def test_the_same_document_gives_the_same_answer(self):
        rng = random.Random(44)
        for _ in range(3):
            spec = _array(rng)
            self.assertEqual(run(copy.deepcopy(doc(**spec))).as_dict(), run(copy.deepcopy(doc(**spec))).as_dict())


if __name__ == "__main__":
    unittest.main()
