import copy
import json
import unittest

import epc_terminal_blocks as T
from epc_terminal_blocks import build, sizes


def circuit(tag="L-01", phases=1, s=2.5, pe=2.5, n=2.5, **extra):
    return {"tag": tag, "phases": phases, "s_mm2": s, "pe_mm2": pe, "neutral_mm2": n, **extra}


class Sizes(unittest.TestCase):
    def setUp(self):
        sizes.clear_cache()

    def test_table_is_sorted_and_pending(self):
        table = T.terminal_sizes()
        self.assertEqual([r["size_mm2"] for r in table], [2.5, 4, 6, 10, 16, 35, 70])
        self.assertEqual(sizes.review_status(), "pending review")

    def test_table_is_a_copy(self):
        T.terminal_sizes()[0]["size_mm2"] = 99
        self.assertEqual(T.terminal_sizes()[0]["size_mm2"], 2.5)

    def test_cache_is_used_and_cleared(self):
        T.terminal_sizes()
        self.assertIn("sizes", sizes._CACHE)
        T.clear_cache()
        self.assertEqual(sizes._CACHE, {})

    def test_accepting_size(self):
        self.assertEqual(T.accepting_size(2.5)["size_mm2"], 2.5)
        self.assertEqual(T.accepting_size(4)["size_mm2"], 4)
        self.assertEqual(T.accepting_size(25)["size_mm2"], 35)
        self.assertEqual(T.accepting_size(50)["size_mm2"], 70)
        self.assertIsNone(T.accepting_size(95))
        self.assertIsNone(T.accepting_size(1))

    def test_custom_table(self):
        table = [{"size_mm2": 9, "accepts_min_mm2": 5, "accepts_max_mm2": 9, "rated_current_a": 1},
                 {"size_mm2": 3, "accepts_min_mm2": 1, "accepts_max_mm2": 6, "rated_current_a": 1}]
        self.assertEqual(T.accepting_size(6, table)["size_mm2"], 3)

    def test_data_file_is_marked_pending(self):
        data = json.loads(sizes.DATA_FILE.read_text(encoding="utf-8"))
        self.assertEqual((data["review_status"], data["clause"]), ("pending review", "no clause"))


class Conductors(unittest.TestCase):
    def test_single_phase(self):
        c = build._circuit(circuit(), 1)
        self.assertEqual([r for r, _ in T.conductors(c)], ["L", "N", "PE"])

    def test_three_phase(self):
        c = build._circuit(circuit(phases=3), 1)
        self.assertEqual([r for r, _ in T.conductors(c)], ["L1", "L2", "L3", "N", "PE"])

    def test_absent_neutral_and_pe(self):
        c = build._circuit(circuit(phases=3, pe=None, n=None), 1)
        self.assertEqual([r for r, _ in T.conductors(c)], ["L1", "L2", "L3"])


class BuildList(unittest.TestCase):
    def setUp(self):
        sizes.clear_cache()
        self.circuits = [circuit("L-01", s=10, pe=10, n=10, description="LIGHTS", device="MCB (25 A)", in_a=25),
                         circuit("M-01", phases=3, s=4, pe=4, n=None, in_a=20), circuit("SUB", phases=3, s=95, pe=50, n=50)]
        self.result = T.build_terminal_list("TS", self.circuits)

    def test_structure(self):
        self.assertEqual(set(self.result), {"board", "strips", "totals", "assumptions", "norm_records", "issues"})
        self.assertEqual(self.result["board"], "TS")
        self.assertEqual(self.result["norm_records"], ["terminal_blocks.params.terminal_sizes"])
        self.assertTrue(any("pending review" in a for a in self.result["assumptions"]))

    def test_ids_are_sequential_and_deterministic(self):
        ids = [t["id"] for r in self.result["strips"][0]["rows"] for t in r["terminals"]]
        self.assertEqual(ids, [f"X1:{n}" for n in range(1, 13)])
        self.assertEqual(self.result, T.build_terminal_list("TS", copy.deepcopy(self.circuits)))

    def test_counts(self):
        rows = self.result["strips"][0]["rows"]
        self.assertEqual([r["conductors"] for r in rows], [3, 4, 5])
        self.assertEqual(self.result["totals"]["terminals"], 12)

    def test_totals(self):
        self.assertEqual(self.result["totals"]["by_section"], {"4": 4, "10": 3, "50": 2, "95": 3})
        self.assertEqual(self.result["totals"]["by_section"]["95"], 3)
        self.assertEqual(self.result["totals"]["by_terminal_size"]["none"], 3)

    def test_no_terminal_accepts_section(self):
        self.assertIn("SUB/L1: no terminal size accepts section 95 mm2", self.result["issues"])
        bad = self.result["strips"][0]["rows"][2]["terminals"][0]
        self.assertIsNone(bad["terminal_size_mm2"])
        self.assertIsNone(bad["terminal_rated_a"])

    def test_absent_neutral_is_reported(self):
        self.assertIn("M-01: no neutral section reported, no neutral terminal listed", self.result["issues"])

    def test_absent_pe_is_reported(self):
        r = T.build_terminal_list("TS", [circuit(pe=None)])
        self.assertIn("L-01: no PE section reported, no PE terminal listed", r["issues"])
        self.assertEqual(r["totals"]["terminals"], 2)

    def test_terminal_rating_below_current(self):
        r = T.build_terminal_list("TS", [circuit(s=2.5, in_a=32)])
        self.assertTrue(any("below the circuit current" in i for i in r["issues"]))
        ok = T.build_terminal_list("TS", [circuit(s=2.5, in_a=16)])
        self.assertEqual(ok["issues"], [])

    def test_start_strip(self):
        r = T.build_terminal_list("TS", [circuit()], start_strip="XA")
        self.assertEqual(r["strips"][0]["strip"], "XA")
        self.assertEqual(r["strips"][0]["rows"][0]["terminals"][0]["id"], "XA:1")

    def test_input_not_modified(self):
        before = copy.deepcopy(self.circuits)
        T.build_terminal_list("TS", self.circuits)
        self.assertEqual(self.circuits, before)

    def test_render_rows(self):
        flat = T.render_rows(self.result)
        self.assertEqual(len(flat), 12)
        self.assertEqual(flat[0]["terminal"], "X1:1")
        self.assertEqual((flat[0]["board"], flat[0]["circuit"], flat[0]["role"], flat[0]["terminal_size_mm2"]), ("TS", "L-01", "L", 10))
        self.assertIn("no terminal size accepts", flat[-5]["issue"])
        self.assertEqual(flat[0]["issue"], "")


class InvalidInput(unittest.TestCase):
    def assertInvalid(self, *args, text="", **kw):
        with self.assertRaisesRegex(ValueError, text):
            T.build_terminal_list(*args, **kw)

    def test_board_name(self):
        self.assertInvalid("", [circuit()], text="board_name")
        self.assertInvalid(None, [circuit()], text="board_name")

    def test_strip(self):
        for bad in ("1X", "", "X 1", 5):
            self.assertInvalid("TS", [circuit()], start_strip=bad, text="start_strip")

    def test_circuits(self):
        for bad in ([], None, "x"):
            self.assertInvalid("TS", bad, text="circuits")

    def test_circuit_shape(self):
        self.assertInvalid("TS", ["x"], text="must be an object")
        self.assertInvalid("TS", [{**circuit(), "foo": 1}], text="unknown key")
        self.assertInvalid("TS", [circuit(tag="")], text="tag")

    def test_phases(self):
        for bad in (2, None, True, "3"):
            self.assertInvalid("TS", [circuit(phases=bad)], text="phases")

    def test_numbers(self):
        for bad in (0, -1, None, True, float("nan"), "4"):
            self.assertInvalid("TS", [circuit(s=bad)], text="s_mm2")
        self.assertInvalid("TS", [circuit(pe=0)], text="pe_mm2")
        self.assertInvalid("TS", [circuit(n=-2)], text="neutral_mm2")
        self.assertInvalid("TS", [circuit(in_a=0)], text="in_a")

    def test_duplicate_tags(self):
        self.assertInvalid("TS", [circuit("A"), circuit("A")], text="duplicate circuit tag")


if __name__ == "__main__":
    unittest.main()
