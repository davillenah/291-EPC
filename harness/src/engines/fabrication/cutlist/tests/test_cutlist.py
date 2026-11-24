"""Tests of the cut-list engine: pure functions, small synthetic parts."""
import copy
import unittest

import epc_cutlist
from epc_cutlist import CutlistError, build_cutlist, render_rows


def part(ident, length, **changes):
    base = {"id": ident, "material": "steel", "length_mm": length}
    base.update(changes)
    return base


def plan(parts, stock=None, kerf=0, **kw):
    return build_cutlist(stock or {"steel": [6000]}, parts, kerf_mm=kerf, **kw)


class KerfTests(unittest.TestCase):
    def test_required(self):
        with self.assertRaisesRegex(ValueError, "kerf_mm is required"):
            build_cutlist({"steel": [6000]}, [part("A", 100)])

    def test_zero_allowed(self):
        self.assertEqual(plan([part("A", 100)])["totals"]["kerf_mm_total"], 0.0)

    def test_negative_and_invalid_rejected(self):
        for bad in (-1, float("nan"), "3", True):
            with self.assertRaisesRegex(ValueError, "kerf_mm must be"):
                plan([part("A", 100)], kerf=bad)

    def test_every_cut_consumes_the_kerf(self):
        result = plan([part("A", 1000, quantity=2)], kerf=5)
        self.assertEqual(result["bars"][0]["used_mm"], 2010.0)
        self.assertEqual(result["totals"]["kerf_mm_total"], 10.0)

    def test_kerf_can_make_a_part_not_fit(self):
        with self.assertRaises(CutlistError) as ctx:
            plan([part("A", 6000)], kerf=1)
        self.assertEqual(ctx.exception.code, "err_part_too_long")


class PackingTests(unittest.TestCase):
    def test_exact_fit_uses_one_bar(self):
        result = plan([part("A", 3000, quantity=2)])
        self.assertEqual((result["totals"]["bars"], result["bars"][0]["left_mm"]), (1, 0.0))

    def test_best_fit_decreasing(self):
        # 4000, 3000, 2000, 2000, 1000: first bar 4000+2000, second 3000+2000+1000
        result = plan([part("A", 4000), part("B", 3000), part("C", 2000, quantity=2), part("D", 1000)])
        self.assertEqual(result["totals"]["bars"], 2)
        self.assertEqual(sorted(b["used_mm"] for b in result["bars"]), [6000.0, 6000.0])

    def test_each_piece_goes_where_it_leaves_least_waste(self):
        result = plan([part("A", 4000), part("B", 3000), part("C", 1800), part("D", 1500)])
        placed = {p["part_id"]: b["bar_id"] for b in result["bars"] for p in b["parts"]}
        self.assertEqual(placed["A"], placed["C"])  # 4000 + 1800 leaves 200; 4000 + 1500 would leave 500

    def test_deterministic_and_order_independent(self):
        parts = [part("A", 1700), part("B", 2300, quantity=2), part("C", 900)]
        first = plan(parts)
        again = plan(list(reversed(parts)))
        self.assertEqual(first["bars"], again["bars"])
        self.assertEqual(first, plan(copy.deepcopy(parts)))

    def test_quantity_expands_to_pieces(self):
        result = plan([part("A", 500, quantity=4)])
        self.assertEqual([p["index"] for p in result["bars"][0]["parts"]], [1, 2, 3, 4])

    def test_materials_are_planned_apart(self):
        result = build_cutlist({"steel": [6000], "tray": [3000]}, [part("A", 2000), part("T", 2500, material="tray")], kerf_mm=0)
        self.assertEqual(set(result["summary"]), {"steel", "tray"})
        self.assertEqual({b["material"] for b in result["bars"]}, {"steel", "tray"})

    def test_material_names_are_case_insensitive(self):
        result = build_cutlist({"Steel": [6000]}, [part("A", 100, material="STEEL")], kerf_mm=0)
        self.assertEqual(result["bars"][0]["material"], "steel")


class StockTests(unittest.TestCase):
    def test_smallest_stock_that_holds_the_piece(self):
        result = plan([part("A", 2500)], stock={"steel": [6000, 3000]})
        self.assertEqual(result["bars"][0]["stock_length_mm"], 3000.0)

    def test_longer_stock_when_the_short_one_is_too_short(self):
        result = plan([part("A", 4000)], stock={"steel": [3000, 6000]})
        self.assertEqual(result["bars"][0]["stock_length_mm"], 6000.0)

    def test_count_limits_the_bars(self):
        stock = {"steel": [{"length_mm": 3000, "count": 1}, {"length_mm": 6000}]}
        result = plan([part("A", 2500, quantity=2)], stock=stock)
        self.assertEqual(sorted(b["stock_length_mm"] for b in result["bars"]), [3000.0, 6000.0])

    def test_limited_stock_is_exhausted(self):
        with self.assertRaises(CutlistError) as ctx:
            plan([part("A", 2500, quantity=3)], stock={"steel": [{"length_mm": 3000, "count": 2}]})
        self.assertEqual(ctx.exception.code, "err_stock_exhausted")

    def test_the_input_counts_are_not_consumed(self):
        stock = {"steel": [{"length_mm": 3000, "count": 2}]}
        before = copy.deepcopy(stock)
        plan([part("A", 2500, quantity=2)], stock=stock)
        self.assertEqual(stock, before)

    def test_equal_lengths_are_merged(self):
        result = plan([part("A", 2500, quantity=3)], stock={"steel": [{"length_mm": 3000, "count": 1}, {"length_mm": 3000, "count": 2}]})
        self.assertEqual(result["totals"]["bars"], 3)

    def test_missing_material_stock(self):
        with self.assertRaises(CutlistError) as ctx:
            build_cutlist({"tray": [3000]}, [part("A", 100)], kerf_mm=0)
        self.assertEqual(ctx.exception.code, "err_stock_missing_material")

    def test_cable_drums(self):
        stock = {"cable": [{"length_mm": 500000, "count": 1}]}
        result = build_cutlist(stock, [part("C1", 120000, material="cable"), part("C2", 80000, material="cable", quantity=2)], kerf_mm=0)
        self.assertEqual(result["totals"]["bars"], 1)
        self.assertEqual(result["bars"][0]["left_mm"], 220000.0)


class MarksTests(unittest.TestCase):
    def marks(self, **changes):
        return build_cutlist({"steel": [6000]}, [part("A", 1000, **changes)], kerf_mm=0)["groups"][0]["marks"]

    def test_square_cut_has_no_mark(self):
        self.assertEqual(self.marks(), [])

    def test_same_direction(self):
        self.assertEqual(self.marks(angle_1_deg=45, angle_2_deg=45), ["-"])
        self.assertEqual(self.marks(angle_1_deg=-30, angle_2_deg=-45), ["-"])

    def test_opposite_direction_has_no_mark(self):
        self.assertEqual(self.marks(angle_1_deg=45, angle_2_deg=-45), [])

    def test_derived_angle(self):
        self.assertEqual(self.marks(angle_1_deg=45, angle_2_deg=45, angle_source="derived"), ["~", "-"])

    def test_unknown_angle_is_marked_and_reported(self):
        result = build_cutlist({"steel": [6000]}, [part("A", 1000, angle_source="unknown")], kerf_mm=0)
        self.assertEqual(result["groups"][0]["marks"], ["?"])
        self.assertEqual(result["issues"], ["A: angle unknown (define it before cutting)"])

    def test_legend_has_both_languages_for_the_marks_used(self):
        result = build_cutlist({"steel": [6000]}, [part("A", 1000, angle_1_deg=45, angle_2_deg=45)], kerf_mm=0)
        self.assertEqual(list(result["marks_legend"]), ["-"])
        self.assertTrue(result["marks_legend"]["-"]["en"] and result["marks_legend"]["-"]["es"])


class GroupingTests(unittest.TestCase):
    def test_equal_parts_are_one_line(self):
        result = plan([part("A", 1000.04, quantity=2, size="L50"), part("B", 1000.0, size="L50"), part("C", 1000, size="L40")])
        lines = {(g["size"], g["length_mm"]): g for g in result["groups"]}
        self.assertEqual(lines[("L50", 1000.0)]["quantity"], 3)
        self.assertEqual(lines[("L50", 1000.0)]["ids"], ["A", "B"])
        self.assertEqual(lines[("L40", 1000.0)]["quantity"], 1)

    def test_different_angles_are_different_lines(self):
        result = plan([part("A", 1000, angle_1_deg=45), part("B", 1000)])
        self.assertEqual(len(result["groups"]), 2)


class InputTests(unittest.TestCase):
    def check(self, code, **kw):
        with self.assertRaises(CutlistError) as ctx:
            build_cutlist(kw.get("stock", {"steel": [6000]}), kw.get("parts", [part("A", 100)]), kerf_mm=kw.get("kerf", 0))
        self.assertEqual(ctx.exception.code, code)
        self.assertTrue(ctx.exception.en and ctx.exception.es)

    def test_empty_parts_and_stock(self):
        self.check("err_parts_empty", parts=[])
        self.check("err_stock_empty", stock={})

    def test_duplicate_ids(self):
        self.check("err_duplicate_part_ids", parts=[part("A", 100), part("A", 200)])

    def test_unknown_key_and_not_object(self):
        self.check("err_unknown_keys", parts=[part("A", 100, colour="red")])
        self.check("err_not_object", parts=["A"])

    def test_length_and_quantity(self):
        for bad in (0, -5, "10", True, float("inf")):
            self.check("err_not_positive_number", parts=[part("A", bad)])
        for bad in (0, 1.5, "2", True):
            self.check("err_not_integer", parts=[part("A", 100, quantity=bad)])

    def test_angles(self):
        for bad in (91, -91, "45", True):
            self.check("err_angle_invalid", parts=[part("A", 100, angle_1_deg=bad)])
        self.check("err_angle_source_invalid", parts=[part("A", 100, angle_source="guess")])

    def test_stock_values(self):
        self.check("err_not_positive_number", stock={"steel": [0]})
        self.check("err_not_integer", stock={"steel": [{"length_mm": 3000, "count": 0}]})
        self.check("err_unknown_keys", stock={"steel": [{"length_mm": 3000, "price": 1}]})


class OutputTests(unittest.TestCase):
    def test_totals_add_up(self):
        result = plan([part("A", 2500, quantity=3), part("B", 1000, quantity=2)], kerf=3)
        t = result["totals"]
        self.assertAlmostEqual(t["stock_mm"], t["used_mm"] + t["waste_mm"])
        self.assertAlmostEqual(t["used_mm"], t["net_mm"] + t["kerf_mm_total"])
        self.assertEqual(t["parts"], 5)

    def test_every_bar_respects_its_length(self):
        result = plan([part(f"P{n}", 400 + 37 * n, quantity=3) for n in range(1, 12)], kerf=3)
        for bar in result["bars"]:
            self.assertLessEqual(bar["used_mm"], bar["stock_length_mm"] + 1e-9)
            self.assertGreaterEqual(bar["left_mm"], -1e-9)

    def test_render_rows(self):
        rows = render_rows(plan([part("A", 1000, quantity=2, angle_1_deg=45, angle_2_deg=45)]))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["marks"], "-")
        self.assertEqual(rows[0]["bar_id"], "steel-001")

    def test_assumptions_are_bilingual(self):
        for a in plan([part("A", 100)])["assumptions"]:
            self.assertTrue(a["en"] and a["es"])

    def test_public_names(self):
        from epc_cutlist import api
        self.assertEqual(set(epc_cutlist.__all__), {"build_cutlist", "render_rows", "CutlistError"})
        self.assertEqual(set(api.__all__), set(epc_cutlist.__all__))


if __name__ == "__main__":
    unittest.main()
