import unittest

from epc_plan import tray_levels as L


class TestCrossings(unittest.TestCase):
    def test_the_higher_run_is_the_upper_one(self):
        a = [(0, 0, 600), (10, 0, 600)]
        b = [(5, -5, 0), (5, 5, 0)]
        (c,) = L.crossings(a, b, 300)
        self.assertEqual((c["upper"], c["ok"], c["gap"]), ("a", True, 600))
        self.assertEqual(c["at"], (5.0, 0.0))

    def test_too_little_gap_is_a_conflict(self):
        (c,) = L.crossings([(0, 0, 100), (10, 0, 100)], [(5, -5, 0), (5, 5, 0)], 300)
        self.assertFalse(c["ok"])

    def test_parallel_runs_do_not_cross(self):
        self.assertEqual(L.crossings([(0, 0, 0), (10, 0, 0)], [(0, 5, 0), (10, 5, 0)], 300), [])


class TestBreak(unittest.TestCase):
    def test_a_line_under_the_upper_tray_is_cut(self):
        pieces = L.break_under([((0.0, 0.0), (10.0, 0.0))], [(5.0, -5.0), (5.0, 5.0)], 2.0, 0.5)
        self.assertEqual(sorted(round(p[1][0] - p[0][0], 6) for p in pieces), [3.5, 3.5])

    def test_a_line_away_from_it_stays(self):
        line = ((0.0, 20.0), (10.0, 20.0))
        self.assertEqual(L.break_under([line], [(5.0, -5.0), (5.0, 5.0)], 2.0, 0.5), [line])


class TestProfileAndRiser(unittest.TestCase):
    def test_a_rise_gives_a_side_view_with_two_edges(self):
        out = L.profile([(0, 0, 0), (5, 0, 0), (5, 0, 3), (10, 0, 3)], 1.0, 0.5)
        self.assertGreater(len(out["lines"]), 4)

    def test_the_riser_has_a_frame_and_two_diagonals(self):
        self.assertEqual(len(L.riser((0, 0), 2, 4)["lines"]), 6)


if __name__ == "__main__":
    unittest.main()
