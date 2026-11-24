"""Corner geometry, join derivation and the outlines of the walls engine (hand-checked numbers)."""
import math
import unittest

from epc_walls import WallsError, bands, derive, inputs, outlines


def area(poly):
    n = len(poly)
    return abs(sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))) / 2


def wall(i, a, b, t=0.2, **kw):
    return {"id": i, "a": a, "b": b, "t": t, **kw}


class JoinTests(unittest.TestCase):
    def test_l_t_x_and_keys(self):
        ws = [wall("A", (0, 0), (4, 0)), wall("B", (4, 0), (4, 3)), wall("C", (2, 0), (2, -3)), wall("D", (6, -1), (6, 1)), wall("E", (5, 0), (7, 0))]
        kinds = {r["key"]: r["kind"] for r in outlines(ws, tol=0.001)["joins"]}
        self.assertEqual(kinds["A:end|B:start"], "L")
        self.assertEqual(kinds["A:mid|C:start"], "T")
        self.assertEqual(kinds["D:mid|E:mid"], "X")

    def test_key_does_not_depend_on_order(self):
        ws = [wall("A", (0, 0), (4, 0)), wall("B", (4, 0), (4, 3))]
        self.assertEqual(derive(inputs.walls(ws), 0.001), derive(inputs.walls(ws[::-1]), 0.001))

    def test_join_off(self):
        ws = [wall("A", (0, 0), (4, 0), join_off={"b": True}), wall("B", (4, 0), (4, 3))]
        self.assertEqual(outlines(ws, tol=0.001)["joins"], [])


class CornerTests(unittest.TestCase):
    def test_l_mitre_90(self):
        r = outlines([wall("A", (0, 0), (4, 0)), wall("B", (4, 0), (4, 3))], tol=0.001)
        total = area(r["walls"]["A"]["outline"]) + area(r["walls"]["B"]["outline"])
        self.assertAlmostEqual(total, 0.2 * 4 + 0.2 * 3, places=6)
        self.assertEqual(r["joins"][0]["applied"], "mitre")

    def test_l_butt_through_a(self):
        r = outlines([wall("A", (0, 0), (4, 0)), wall("B", (4, 0), (4, 3))], tol=0.001, styles={"A:end|B:start": {"style": "butt", "through": "A"}})
        self.assertAlmostEqual(max(p[0] for p in r["walls"]["A"]["outline"]), 4.1)
        self.assertAlmostEqual(min(p[1] for p in r["walls"]["B"]["outline"]), 0.1)

    def test_l_square_through_a(self):
        r = outlines([wall("A", (0, 0), (4, 0)), wall("B", (4, 0), (4, 3))], tol=0.001, styles={"A:end|B:start": {"style": "square", "through": "A"}})
        self.assertAlmostEqual(max(p[0] for p in r["walls"]["A"]["outline"]), 4.1)

    def test_style_as_plain_text(self):
        r = outlines([wall("A", (0, 0), (4, 0)), wall("B", (4, 0), (4, 3))], tol=0.001, styles={"A:end|B:start": "butt"})
        self.assertEqual(r["joins"][0]["applied"], "butt")

    def test_bad_through(self):
        with self.assertRaises(WallsError) as c:
            outlines([wall("A", (0, 0), (4, 0)), wall("B", (4, 0), (4, 3))], tol=0.001, styles={"A:end|B:start": {"style": "butt", "through": "Z"}})
        self.assertEqual(c.exception.code, "err_style_invalid")

    def test_l_135(self):
        b = (4 + 3 * math.cos(math.radians(45)), 3 * math.sin(math.radians(45)))
        r = outlines([wall("A", (0, 0), (4, 0)), wall("B", (4, 0), b)], tol=0.001)
        self.assertEqual(r["joins"][0]["applied"], "mitre")
        self.assertEqual(r["issues"], [])

    def test_unequal_thickness(self):
        r = outlines([wall("A", (0, 0), (4, 0), 0.1), wall("B", (4, 0), (4, 3), 0.3)], tol=0.001)
        self.assertEqual(r["joins"][0]["applied"], "mitre")
        self.assertEqual(len(r["walls"]["A"]["outline"]), 4)

    def test_sharp_corner_falls_back_to_square(self):
        b = (4 - 3 * math.cos(math.radians(5)), 3 * math.sin(math.radians(5)))
        r = outlines([wall("A", (0, 0), (4, 0)), wall("B", (4, 0), b)], tol=0.001)
        self.assertEqual(r["joins"][0]["applied"], "square")
        self.assertEqual(r["issues"][0]["code"], "note_corner_square")
        self.assertIn("inglete", r["issues"][0]["es"])

    def test_collinear_stays_square(self):
        r = outlines([wall("A", (0, 0), (4, 0)), wall("B", (4, 0), (8, 0))], tol=0.001)
        self.assertEqual(r["joins"][0]["applied"], "square")

    def test_t_90_and_60(self):
        r = outlines([wall("H", (0, 0), (6, 0)), wall("S", (3, 0), (3, 3))], tol=0.001)
        self.assertEqual(r["joins"][0]["kind"], "T")
        self.assertAlmostEqual(min(p[1] for p in r["walls"]["S"]["outline"]), 0.1)
        s = (3 + 3 * math.cos(math.radians(60)), 3 * math.sin(math.radians(60)))
        r = outlines([wall("H", (0, 0), (6, 0)), wall("S", (3, 0), s)], tol=0.001)
        ys = sorted(p[1] for p in r["walls"]["S"]["outline"])
        self.assertAlmostEqual(ys[0], 0.1)
        self.assertAlmostEqual(ys[1], 0.1)

    def test_t_stem_on_the_other_side(self):
        r = outlines([wall("H", (0, 0), (6, 0)), wall("S", (3, 0), (3, -3))], tol=0.001)
        self.assertAlmostEqual(max(p[1] for p in r["walls"]["S"]["outline"]), -0.1)

    def test_t_with_stem_end_at_the_wall_end(self):
        r = outlines([wall("H", (0, 0), (6, 0)), wall("S", (3, 3), (3, 0))], tol=0.001)
        self.assertAlmostEqual(min(p[1] for p in r["walls"]["S"]["outline"]), 0.1)

    def test_node_with_three_ends_stays_square(self):
        ws = [wall("A", (0, 0), (4, 0)), wall("B", (4, 0), (4, 3)), wall("C", (4, 0), (6, -2))]
        r = outlines(ws, tol=0.001)
        self.assertTrue(any(i["code"] == "note_node_complex" for i in r["issues"]))

    def test_x_records_only(self):
        r = outlines([wall("A", (0, 0), (4, 0)), wall("B", (2, -2), (2, 2))], tol=0.001)
        self.assertEqual(r["joins"][0]["applied"], "cross")
        self.assertAlmostEqual(area(r["walls"]["A"]["outline"]), 0.8)


class LayerTests(unittest.TestCase):
    LAYERS = [{"mat": "a", "t": 10, "function": "finish"}, {"mat": "b", "t": 100, "function": "structure"}, {"mat": "c", "t": 0, "function": "membrane"}]

    def test_thickness_is_the_sum_and_bands(self):
        r = outlines([{"id": "A", "a": (0, 0), "b": (4000, 0), "layers": self.LAYERS}], tol=1)
        w = r["walls"]["A"]
        self.assertEqual(w["thickness"], 110)
        self.assertEqual([b["mat"] for b in w["bands"]], ["b", "a"])
        self.assertEqual(w["bands"][1]["hi"], 55)

    def test_exterior_on_the_right(self):
        b = bands(self.LAYERS, "right")
        self.assertEqual(b[0]["mat"], "a")
        self.assertEqual(b[0]["lo"], -55)

    def test_priority_default_and_own(self):
        layers = [{"mat": "a", "t": 10, "function": "finish", "priority": 900}, {"mat": "b", "t": 10, "function": "structure"},
                  {"mat": "g", "t": 5, "function": "finish", "kind": "cavity"}]
        self.assertEqual({b["mat"]: b["priority"] for b in bands(layers)}, {"a": 900, "b": 800, "g": 100})


class ErrorTests(unittest.TestCase):
    def check(self, walls, code, **kw):
        kw.setdefault("tol", 0.001)
        with self.assertRaises(WallsError) as c:
            outlines(walls, **kw)
        self.assertEqual(c.exception.code, code)
        self.assertTrue(c.exception.en and c.exception.es and c.exception.en != c.exception.es)

    def test_errors(self):
        a = wall("A", (0, 0), (4, 0))
        self.check([], "err_walls_empty")
        self.check([a, a], "err_duplicate_wall_ids")
        self.check([wall("A", (0, 0), (0, 0))], "err_wall_zero_length")
        self.check([wall("A", (0, 0), (4, 0), -1)], "err_not_positive_number")
        self.check([{"id": "A", "a": (0, 0), "b": (4, 0)}], "err_wall_no_thickness")
        self.check([{"id": "A", "a": (0, 0), "b": (4, 0), "t": 1, "layers": [{"mat": "x", "t": 1, "function": "finish"}]}], "err_wall_both_thickness")
        self.check([[1]], "err_not_object")
        self.check([{**a, "z": 1}], "err_unknown_keys")
        self.check([{**a, "a": "x"}], "err_not_point")
        self.check([a], "err_not_positive_number", tol=0)
        self.check([a], "err_style_invalid", styles={"k": "round"})
        self.check([{**a, "ext_side": "up"}], "err_unknown_keys")
        self.check([{"id": "", "a": (0, 0), "b": (1, 0), "t": 1}], "err_not_text")

    def test_layer_errors(self):
        def lay(**kw):
            return [{"id": "A", "a": (0, 0), "b": (4, 0), "layers": [{"mat": "m", "t": 10, "function": "finish", **kw}]}]
        self.check(lay(t=-1), "err_layer_thickness")
        self.check(lay(function="paint"), "err_layer_function")
        self.check(lay(kind="hole"), "err_layer_kind")
        self.check(lay(t=0), "err_layer_zero_not_membrane")
        self.check(lay(priority=5000), "err_layer_priority")
        self.check(lay(mat=""), "err_not_text")
        self.check([{"id": "A", "a": (0, 0), "b": (4, 0), "layers": []}], "err_layers_count")
        self.check([{"id": "A", "a": (0, 0), "b": (4, 0), "layers": [{"mat": "m", "t": 0, "function": "membrane"}]}], "err_layers_no_thickness")
        self.check([{"id": "A", "a": (0, 0), "b": (4, 0), "layers": ["x"]}], "err_not_object")


if __name__ == "__main__":
    unittest.main()
