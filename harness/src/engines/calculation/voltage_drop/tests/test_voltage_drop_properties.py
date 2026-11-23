"""OPT-13: invariants of the voltage-drop formulas over many generated inputs (seeded, standard library only).

No norm value is used: R, X, cos(phi), currents and lengths are generated, and each test states a property that has to hold for all of them.
"""
import math
import random
import unittest

from epc_voltage_drop import (caida_tension, drop_voltage_single_phase_v, drop_voltage_three_phase_v, longitud_maxima_m,
                              porcentaje)

SAMPLES = 300


def _cases(seed):
    rng = random.Random(seed)
    for _ in range(SAMPLES):
        yield {"i_a": rng.uniform(0.5, 800.0), "longitud_m": rng.uniform(1.0, 2000.0), "r_ohm_km": rng.uniform(0.01, 20.0),
               "x_ohm_km": rng.uniform(0.0, 0.2), "fp": rng.uniform(0.5, 1.0)}


class VoltageDropProperties(unittest.TestCase):
    def test_more_current_or_more_length_never_lowers_the_drop(self):
        for c in _cases(1):
            base = drop_voltage_three_phase_v(**c)
            for key in ("i_a", "longitud_m"):
                more = dict(c, **{key: c[key] * 1.5})
                with self.subTest(case=c, grown=key):
                    self.assertGreaterEqual(drop_voltage_three_phase_v(**more), base)

    def test_a_higher_resistance_never_lowers_the_drop(self):
        for c in _cases(2):
            with self.subTest(case=c):
                self.assertGreaterEqual(drop_voltage_three_phase_v(**dict(c, r_ohm_km=c["r_ohm_km"] * 2)), drop_voltage_three_phase_v(**c))

    def test_the_drop_is_linear_in_current_and_in_length(self):
        for c in _cases(3):
            base = drop_voltage_single_phase_v(**c)
            for key in ("i_a", "longitud_m"):
                with self.subTest(case=c, scaled=key):
                    self.assertAlmostEqual(drop_voltage_single_phase_v(**dict(c, **{key: c[key] * 3})), 3 * base, delta=abs(base) * 1e-9 + 1e-12)

    def test_three_phase_over_single_phase_is_root_three_over_two(self):
        for c in _cases(4):
            with self.subTest(case=c):
                self.assertAlmostEqual(drop_voltage_three_phase_v(**c) / drop_voltage_single_phase_v(**c), math.sqrt(3.0) / 2.0, places=9)

    def test_the_percentage_is_the_volts_over_the_nominal_voltage(self):
        for c in _cases(5):
            for fases, un in ((1, 230.0), (3, 400.0)):
                result = caida_tension(fases, un_v=un, **c)
                with self.subTest(case=c, phases=fases):
                    self.assertAlmostEqual(result["delta_u_pct"], porcentaje(result["delta_u_v"], un), places=9)

    def test_the_maximum_length_gives_exactly_the_allowed_drop(self):
        for c in _cases(6):
            limit_v = 0.03 * 400.0
            for fases, drop in ((3, drop_voltage_three_phase_v), (1, drop_voltage_single_phase_v)):
                args = {k: c[k] for k in ("i_a", "r_ohm_km", "x_ohm_km", "fp")}
                length = longitud_maxima_m(fases, limit_v, **args)
                with self.subTest(case=c, phases=fases):
                    self.assertAlmostEqual(drop(longitud_m=length, **args), limit_v, delta=limit_v * 1e-9)

    def test_a_larger_allowed_drop_never_shortens_the_maximum_length(self):
        for c in _cases(7):
            args = {k: c[k] for k in ("i_a", "r_ohm_km", "x_ohm_km", "fp")}
            with self.subTest(case=c):
                self.assertGreater(longitud_maxima_m(3, 24.0, **args), longitud_maxima_m(3, 12.0, **args))


if __name__ == "__main__":
    unittest.main()
