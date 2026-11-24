"""A tray with a width is drawn as a ladder (two rails and rungs), not as a single line."""
import math
import unittest

import ezdxf

from epc_plan import dxfout as D


class TestLadder(unittest.TestCase):
    def test_a_straight_tray_has_two_rails_and_a_rung_every_pitch(self):
        lines = D._ladder_lines([(0.0, 0.0), (1000.0, 0.0)], 300.0, 250.0)
        rails = [l for l in lines if l[0][1] == l[1][1]]
        rungs = [l for l in lines if l[0][0] == l[1][0]]
        self.assertEqual(sorted((l[0][1], l[1][1]) for l in rails), [(-150.0, -150.0), (150.0, 150.0)])
        self.assertEqual(sorted(l[0][0] for l in rungs), [250.0, 500.0, 750.0])         # none at the ends, they belong to the joints
        self.assertTrue(all(math.isclose(abs(l[0][1] - l[1][1]), 300.0) for l in rungs))

    def test_a_rung_exactly_at_the_end_is_not_repeated(self):
        rungs = [l for l in D._ladder_lines([(0.0, 0.0), (1000.0, 0.0)], 300.0, 500.0) if l[0][0] == l[1][0]]
        self.assertEqual([l[0][0] for l in rungs], [500.0])

    def test_the_rails_of_a_bend_meet_at_the_corner(self):
        left = D._offset_path([(0.0, 0.0), (3000.0, 0.0), (3000.0, 2000.0)], 150.0)
        self.assertEqual(left, [(0.0, 150.0), (2850.0, 150.0), (2850.0, 2000.0)])
        right = D._offset_path([(0.0, 0.0), (3000.0, 0.0), (3000.0, 2000.0)], -150.0)
        self.assertEqual(right, [(0.0, -150.0), (3150.0, -150.0), (3150.0, 2000.0)])

    def test_repeated_points_and_a_single_point_do_not_break_it(self):
        self.assertEqual(D._offset_path([(1.0, 1.0), (1.0, 1.0)], 5.0), [(1.0, 1.0)])
        self.assertEqual(D._ladder_lines([(0.0, 0.0), (0.0, 0.0), (500.0, 0.0)], 100.0, 250.0)[0], ((0.0, 50.0), (500.0, 50.0)))

    def test_a_fold_back_keeps_a_finite_corner(self):
        out = D._offset_path([(0.0, 0.0), (1000.0, 0.0), (0.0, 0.0)], 10.0)
        self.assertTrue(all(math.isfinite(c) for p in out for c in p))

    def _block_lines(self, attrs, pitch_mm):
        doc = ezdxf.new("R2018")
        blk = doc.blocks.new("T")
        D._add_tray_detail(blk, {"attrs": attrs}, [(0.0, 0.0), (3.0, 0.0)], (0.0, 0.0), 1.0, pitch_mm, "L")      # scale 1: drawing unit = metre
        return [e for e in blk if e.dxftype() == "LINE"]

    def test_the_detail_is_drawn_only_for_a_tray_with_a_width_and_a_pitch(self):
        self.assertEqual(len(self._block_lines({"ancho_mm": 300}, 500)), 2 + 5)                     # two rails and rungs at 0.5 .. 2.5 m
        self.assertEqual(self._block_lines({}, 500), [])
        self.assertEqual(self._block_lines({"ancho_mm": "x"}, 500), [])
        self.assertEqual(self._block_lines({"ancho_mm": 300}, 0), [])


if __name__ == "__main__":
    unittest.main()
