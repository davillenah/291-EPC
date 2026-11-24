"""Rectangular and polar arrays: hand-checked positions and every error."""
import unittest

from epc_arrays import ArraysError, api, polar, rectangular

LIMIT = dict(max_items=1000)


def points(items):
    return [tuple(i["point"]) for i in items]


class RectangularTests(unittest.TestCase):
    def test_grid_row_by_row(self):
        items = rectangular((10, 20), 2, 3, 5, 4, angle_deg=0, **LIMIT)
        self.assertEqual(points(items), [(10, 20), (14, 20), (18, 20), (10, 25), (14, 25), (18, 25)])
        self.assertEqual([(i["index"], i["row"], i["col"]) for i in items][4], (4, 1, 1))
        self.assertEqual({i["rotation"] for i in items}, {0.0})

    def test_turned_grid(self):
        items = rectangular((0, 0), 2, 2, 2, 3, angle_deg=90, **LIMIT)
        self.assertEqual(points(items), [(0, 0), (0, 3), (-2, 0), (-2, 3)])
        self.assertEqual(items[0]["rotation"], 90.0)

    def test_negative_spacing_goes_the_other_way(self):
        self.assertEqual(points(rectangular((0, 0), 1, 3, 1, -2, angle_deg=0, **LIMIT)), [(0, 0), (-2, 0), (-4, 0)])

    def test_one_item_needs_no_spacing(self):
        self.assertEqual(points(rectangular((1, 1), 1, 1, 0, 0, angle_deg=0, **LIMIT)), [(1, 1)])


class PolarTests(unittest.TestCase):
    def test_full_circle_is_spread_evenly(self):
        items = polar((0, 0), (10, 0), 4, 360, rotate_items=True, **LIMIT)
        self.assertEqual(points(items), [(10, 0), (0, 10), (-10, 0), (0, -10)])
        self.assertEqual([i["rotation"] for i in items], [0.0, 90.0, 180.0, 270.0])

    def test_partial_fill_reaches_the_end(self):
        items = polar((0, 0), (10, 0), 3, 90, rotate_items=False, **LIMIT)
        self.assertEqual(points(items), [(10, 0), (7.071067812, 7.071067812), (0, 10)])
        self.assertEqual({i["rotation"] for i in items}, {0.0})

    def test_negative_fill_goes_clockwise(self):
        self.assertEqual(points(polar((0, 0), (10, 0), 2, -90, rotate_items=True, **LIMIT)), [(10, 0), (0, -10)])

    def test_centre_is_not_the_origin(self):
        self.assertEqual(points(polar((5, 5), (6, 5), 2, 180, rotate_items=True, **LIMIT)), [(6, 5), (4, 5)])

    def test_one_item(self):
        self.assertEqual(points(polar((0, 0), (3, 4), 1, 90, rotate_items=True, **LIMIT)), [(3, 4)])


class ErrorTests(unittest.TestCase):
    def check(self, code, call, *args, **kwargs):
        with self.assertRaises(ArraysError) as c:
            call(*args, **kwargs)
        self.assertEqual(c.exception.code, code)
        self.assertTrue(c.exception.en and c.exception.es and c.exception.en != c.exception.es)

    def test_rectangular_errors(self):
        ok = dict(angle_deg=0, **LIMIT)
        self.check("err_not_point", rectangular, "x", 1, 1, 1, 1, **ok)
        self.check("err_not_point", rectangular, (1, True), 1, 1, 1, 1, **ok)
        self.check("err_not_count", rectangular, (0, 0), 0, 1, 1, 1, **ok)
        self.check("err_not_count", rectangular, (0, 0), 1.5, 1, 1, 1, **ok)
        self.check("err_not_number", rectangular, (0, 0), 1, 1, float("nan"), 1, **ok)
        self.check("err_not_number", rectangular, (0, 0), 1, 1, 1, 1, angle_deg="x", max_items=5)
        self.check("err_too_many", rectangular, (0, 0), 10, 10, 1, 1, angle_deg=0, max_items=99)
        self.check("err_not_count", rectangular, (0, 0), 1, 1, 1, 1, angle_deg=0, max_items=0)
        self.check("err_zero_spacing", rectangular, (0, 0), 2, 1, 0, 1, **ok)
        self.check("err_zero_spacing", rectangular, (0, 0), 1, 2, 1, 0, **ok)

    def test_polar_errors(self):
        self.check("err_fill_zero", polar, (0, 0), (1, 0), 3, 0, rotate_items=True, **LIMIT)
        self.check("err_fill_range", polar, (0, 0), (1, 0), 3, 400, rotate_items=True, **LIMIT)
        self.check("err_not_count", polar, (0, 0), (1, 0), 0, 90, rotate_items=True, **LIMIT)
        self.check("err_too_many", polar, (0, 0), (1, 0), 50, 90, rotate_items=True, max_items=10)


class DoorTests(unittest.TestCase):
    def test_the_public_door(self):
        self.assertEqual(sorted(api.__all__), ["ArraysError", "polar", "rectangular"])


if __name__ == "__main__":
    unittest.main()
