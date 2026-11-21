"""epc_drawing.diagram_knowledge: rule evaluation, symbol lookup and the advisory board cross-check (it never changes a result)."""
import json
import sys
import unittest
from pathlib import Path

H = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(H / "src" / "engines" / "cad" / "drawing" / "src"))
from epc_drawing import diagram_knowledge as K  # noqa: E402

EXAMPLE = H / "src" / "engines" / "calculation" / "aea90364" / "examples" / "input_for_sld_V1_calculo.json"


class DiagramKnowledgeUse(unittest.TestCase):
    def test_rules_loaded_from_both_files(self):
        self.assertGreaterEqual(len(K.rules()), 41)
        self.assertTrue(all(r["domain"] == "lv_protection" for r in K.rules("lv_protection")))

    def test_unknown_variable_never_matches(self):
        self.assertEqual([], K.matching({"voltage_level": "LV"}, "lv_protection"))

    def test_current_selects_mcb_then_mccb(self):
        self.assertIn("mcb", {r["then"]["select"] for r in K.matching({"voltage_level": "LV", "rated_current_a": 20, "load_type": "general"}, "lv_protection")})
        self.assertIn("mccb", {r["then"]["select"] for r in K.matching({"voltage_level": "LV", "rated_current_a": 250}, "lv_protection")})

    def test_symbol_lookup(self):
        self.assertEqual("lv_mcb", K.symbol_for("mcb")["sld_symbol"])
        self.assertIsNone(K.symbol_for("pv_rcmu")["sld_symbol"])
        with self.assertRaises(KeyError):
            K.symbol_for("nope")

    def test_check_board_is_advisory_and_does_not_mutate(self):
        calc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        before = json.dumps(calc, sort_keys=True)
        notes = K.check_board(calc)
        self.assertEqual(before, json.dumps(calc, sort_keys=True))
        for n in notes:
            self.assertEqual({"circuit", "drawn", "rule", "suggested", "status", "en", "es"}, set(n))
        self.assertEqual([], K.check_board({"X": {"In": 10, "disp": "MCB (10 A)"}}))
        self.assertEqual("mccb", K.check_board({"X": {"In": 250, "disp": "MCB (250 A)"}})[0]["suggested"][0])


if __name__ == "__main__":
    unittest.main()


class Stage9Notes(unittest.TestCase):
    """Stage 9 lists the rule notes as `note` findings of the verifier calc-check; without a chain it lists none."""

    def test_notes_as_findings(self):
        from types import SimpleNamespace
        sys.path.insert(0, str(H / "src"))
        from disciplines.electrical_lv.stages import calc_check_stage as S
        chain = {"calc": {"detalle": {"X": {"proteccion": {"disp": "MCB (250 A)", "In": 250}}, "Y": {"proteccion": {"disp": "MCB (10 A)", "In": 10}}, "Z": {}}}}
        ctx = SimpleNamespace(engine_cache={"chain": chain}, pipeline_run_id="r1")
        found = S.diagram_findings(ctx, 5)
        self.assertEqual(["F-0005"], [f["id"] for f in found])
        self.assertEqual(("note", "calc-check", "X/device_per_rules"), (found[0]["severity"], found[0]["verifier"], found[0]["field"]))
        self.assertEqual([], S.diagram_findings(SimpleNamespace(engine_cache={}, pipeline_run_id="r1"), 1))
