import unittest

from epc_plan import core, tray_fittings as F

SIZES = {"lip": 15.0, "rung_pitch": 300.0, "rung_width": 30.0, "slot_pitch": 100.0, "slot_length": 60.0, "wire_pitch": 100.0, "radius": 300.0, "joint_pitch": 3000.0,
         "support_spacing": 1500.0, "support_channel": 41.0, "support_overhang": 25.0, "support_rod": 10.0}


class TestFittings(unittest.TestCase):
    def test_every_fitting_draws_lines(self):
        for kind in F.FITTINGS:
            with self.subTest(kind=kind):
                self.assertGreater(len(F.fitting_lines(kind, 300.0, SIZES)), 4)

    def test_an_unknown_fitting_is_the_engines_error(self):
        with self.assertRaises(core.PlanError):
            F.fitting_lines("x", 300.0, SIZES)

    def test_the_same_input_gives_the_same_lines(self):
        self.assertEqual(F.fitting_lines("tee", 300.0, SIZES), F.fitting_lines("tee", 300.0, SIZES))

    def test_the_cross_has_four_arms_and_the_tee_three(self):
        def reach(lines):
            return {(round(max(abs(a[0]), abs(b[0]))), round(max(abs(a[1]), abs(b[1])))) for a, b in lines}
        self.assertIn(1200, {r[1] for r in reach(F.fitting_lines("cross", 300.0, SIZES))})
        ys = [max(a[1], b[1]) for a, b in F.fitting_lines("tee", 300.0, SIZES)]
        self.assertLess(max(ys), 400.0)                              # the tee has no branch upwards


if __name__ == "__main__":
    unittest.main()
