"""The exterior dimensions of a rectangular building (hand-checked numbers), the skipped walls and the errors."""
import unittest

from epc_dims import DimsError, api, dimensions

BOX = [{"id": "S", "a": (0, 0), "b": (8000, 0), "t": 200, "ext_side": "right"},
       {"id": "E", "a": (8000, 0), "b": (8000, 5000), "t": 200, "ext_side": "right"},
       {"id": "N", "a": (8000, 5000), "b": (0, 5000), "t": 200, "ext_side": "right"},
       {"id": "W", "a": (0, 5000), "b": (0, 0), "t": 200, "ext_side": "right"}]
ARGS = dict(tol=1, gap=900, step=600, min_wall=1)


def by(result, edge, kind):
    return [d for d in result["dims"] if d["edge"] == edge and d["kind"] == kind]


class BoxTests(unittest.TestCase):
    def test_totals_and_rows(self):
        r = dimensions(BOX, **ARGS)
        self.assertEqual(r["bounds"], {"x": [-100.0, 8100.0], "y": [-100.0, 5100.0]})
        south, west = by(r, "south", "total")[0], by(r, "west", "total")[0]
        self.assertEqual((south["value"], south["line"]), (8200.0, -1600.0))
        self.assertEqual((west["value"], west["line"]), (5200.0, -1600.0))
        self.assertEqual(by(r, "north", "chain")[0]["line"], 5100 + 900)
        self.assertEqual(by(r, "east", "chain")[0]["line"], 8100 + 900)

    def test_a_single_span_chain_is_not_repeated_over_the_total(self):
        r = dimensions(BOX, **ARGS)
        self.assertEqual(by(r, "south", "chain"), [])
        self.assertEqual(by(r, "west", "chain"), [])

    def test_inner_wall_and_opening(self):
        walls = BOX + [{"id": "P", "a": (4000, 0), "b": (4000, 5000), "t": 150}]
        r = dimensions(walls, openings=[{"id": "V1", "wall": "S", "from": 1000, "width": 1500}], **ARGS)
        values = [d["value"] for d in by(r, "south", "chain")]
        self.assertEqual(values, [1100.0, 1500.0, 1500.0, 4100.0])
        self.assertEqual([d["value"] for d in by(r, "north", "chain")], [4100.0, 4100.0])

    def test_opening_on_a_wall_that_runs_backwards(self):
        r = dimensions(BOX, openings=[{"id": "V", "wall": "N", "from": 1000, "width": 2000}], **ARGS)
        self.assertEqual([d["value"] for d in by(r, "north", "chain")], [5100.0, 2000.0, 1100.0])

    def test_existing_dimensions_are_not_made_again(self):
        first = dimensions(BOX, **ARGS)["dims"]
        again = dimensions(BOX, existing=[{"p1": d["p2"], "p2": d["p1"]} for d in first], **ARGS)
        self.assertEqual(again["dims"], [])

    def test_ids_are_sequential(self):
        self.assertEqual([d["id"] for d in dimensions(BOX, **ARGS)["dims"]], ["D1", "D2", "D3", "D4"])

    def test_the_result_does_not_depend_on_the_order_of_the_walls(self):
        self.assertEqual(dimensions(BOX, **ARGS), dimensions(BOX[::-1], **ARGS))


class SkipTests(unittest.TestCase):
    def test_short_and_oblique_walls_are_noted(self):
        walls = BOX + [{"id": "T", "a": (10, 10), "b": (10.5, 10), "t": 100}, {"id": "O", "a": (1000, 1000), "b": (2000, 1800), "t": 100}]
        r = dimensions(walls, **ARGS)
        codes = [i["code"] for i in r["issues"]]
        self.assertIn("note_wall_skipped_short", codes)
        self.assertIn("note_wall_skipped_oblique", codes)
        self.assertIn("note_not_done", codes)
        self.assertEqual(len(r["dims"]), 4)

    def test_nothing_left(self):
        r = dimensions([{"id": "T", "a": (0, 0), "b": (0.5, 0), "t": 100}], **ARGS)
        self.assertEqual((r["dims"], r["bounds"], r["issues"][0]["code"]), ([], None, "note_no_walls"))
        self.assertIn("ningún muro", r["issues"][0]["es"])

    def test_left_side_exterior(self):
        walls = [{**w, "a": w["b"], "b": w["a"], "ext_side": "left"} for w in BOX]
        self.assertEqual(dimensions(walls, **ARGS)["bounds"], dimensions(BOX, **ARGS)["bounds"])


class ErrorTests(unittest.TestCase):
    def check(self, code, walls=BOX, **kw):
        args = {**ARGS, **kw}
        with self.assertRaises(DimsError) as c:
            dimensions(walls, **args)
        self.assertEqual(c.exception.code, code)
        self.assertTrue(c.exception.en and c.exception.es and c.exception.en != c.exception.es)

    def test_errors(self):
        self.check("err_not_positive_number", tol=0)
        self.check("err_not_positive_number", gap=-1)
        self.check("err_walls_empty", walls=[])
        self.check("err_duplicate_ids", walls=BOX + [BOX[0]])
        self.check("err_not_object", walls=[1])
        self.check("err_unknown_keys", walls=[{**BOX[0], "z": 1}])
        self.check("err_not_text", walls=[{**BOX[0], "id": ""}])
        self.check("err_not_point", walls=[{**BOX[0], "a": "x"}])
        self.check("err_ext_side", walls=[{**BOX[0], "ext_side": "up"}])
        self.check("err_not_positive_number", walls=[{**BOX[0], "t": 0}])

    def test_opening_and_existing_errors(self):
        self.check("err_opening_wall", openings=[{"id": "V", "wall": "Z", "from": 0, "width": 1}])
        self.check("err_opening_range", openings=[{"id": "V", "wall": "S", "from": 7500, "width": 1000}])
        self.check("err_opening_range", openings=[{"id": "V", "wall": "S", "from": "x", "width": 1000}])
        self.check("err_duplicate_ids", openings=[{"id": "V", "wall": "S", "from": 0, "width": 1}] * 2)
        self.check("err_not_point", existing=[{"p1": 1, "p2": (0, 0)}])


class DoorTests(unittest.TestCase):
    def test_the_public_door(self):
        self.assertEqual(sorted(api.__all__), ["DimsError", "dimensions"])


if __name__ == "__main__":
    unittest.main()
