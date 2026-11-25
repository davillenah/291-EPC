"""The metrics by place used to judge the engine against the truth: openings matched by position, wall overlap, thickness error."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import geometric_metrics as gm                                     # noqa: E402


class TestGeometricMetrics(unittest.TestCase):
    def test_openings_match_by_place_within_half_their_width(self):
        truth = [(100.0, 0.0, 100.0), (500.0, 0.0, 80.0)]
        self.assertEqual(gm.match_openings([(130.0, 0.0), (900.0, 0.0)], truth), 1)
        self.assertEqual(gm.match_openings([(100.0, 0.0), (505.0, 0.0)], truth), 2)

    def test_one_found_opening_cannot_match_two_truth_ones(self):
        self.assertEqual(gm.match_openings([(100.0, 0.0)], [(100.0, 0.0, 100.0), (110.0, 0.0, 100.0)]), 1)

    def test_f1_of_nothing_found_where_nothing_is(self):
        self.assertEqual(gm._f1(0, 0, 0)["f1"], 1.0)
        self.assertEqual(gm._f1(0, 3, 0)["precision"], 0.0)

    def test_overlap_of_identical_walls_is_one_and_of_disjoint_is_zero(self):
        walls = [((0.0, 0.0), (400.0, 0.0), 30.0)]
        boxes = gm._wall_boxes(walls)
        self.assertEqual(gm.wall_iou(boxes, boxes), 1.0)
        far = gm._wall_boxes([((0.0, 900.0), (400.0, 900.0), 30.0)])
        self.assertEqual(gm.wall_iou(boxes, far), 0.0)

    def test_thickness_error_is_measured_on_the_wall_it_lies_on(self):
        truth = [{"a": [0, 0], "b": [400, 0], "espesor_cm": 30}]
        self.assertEqual(gm.thickness_error([((0.0, 5.0), (400.0, 5.0), 33.0)], truth), 3.0)


if __name__ == "__main__":
    unittest.main()
