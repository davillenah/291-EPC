"""epc_drawing.diagram_knowledge: rule evaluation, symbol lookup and the advisory board cross-check (it never changes a result)."""
import json
import sys
import unittest
from pathlib import Path

H = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(H / "src" / "engines" / "cad" / "drawing" / "src"))
from epc_drawing import diagram_knowledge as K  # noqa: E402
from epc_drawing import diagram_model as DM  # noqa: E402

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
        self.assertEqual("lv_pv_rcmu", K.symbol_for("pv_rcmu")["sld_symbol"])
        self.assertEqual("placeholder", K.symbol_for("pv_rcmu")["match"])
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


class BoardModel(unittest.TestCase):
    """ADR-0037: one relational model per board, stable ids, no values, branches hang from the parent."""
    CIRCUITS = {"G-02": {"disp": "RCCB 4P 63 A 30 mA", "kind": "feeder"}, "IUG-01": {"disp": "MCB (10 A)", "kind": "lighting", "parent": "G-02"},
                "M-01": {"disp": "MCB > KM > OL (25 A)", "kind": "motor"}, "T-01": {"kind": "sockets"}}

    def test_deterministic_and_stable_ids(self):
        a = DM.build_board_model("TS1", self.CIRCUITS)
        self.assertEqual(a, DM.build_board_model("TS1", dict(reversed(list(self.CIRCUITS.items())))))
        more = dict(self.CIRCUITS, **{"A-00": {"kind": "general"}})
        b = DM.build_board_model("TS1", more)
        for key in ("devices", "loads", "wires", "circuits"):
            self.assertTrue({x["id"] for x in a[key]} <= {x["id"] for x in b[key]}, key)

    def test_chain_from_calculation_and_from_topology(self):
        m = DM.build_board_model("TS1", self.CIRCUITS)
        roles = {d["id"] for d in m["devices"]}
        self.assertTrue({"dev-M-01-mcb", "dev-M-01-contactor", "dev-M-01-thermal_overload_relay", "dev-T-01-rccb", "dev-T-01-mcb"} <= roles)
        self.assertEqual([], m["unmapped"])

    def test_child_hangs_from_the_parent_device(self):
        m = DM.build_board_model("TS1", self.CIRCUITS)
        first = next(w for w in m["wires"] if w["id"] == "wire-IUG-01-1")
        self.assertEqual("dev-G-02-rccb", first["from"]["ref"])
        self.assertFalse(any(x["id"] == "load-G-02" for x in m["loads"]))

    def test_unknown_token_is_reported_not_guessed(self):
        m = DM.build_board_model("TS1", {"X-1": {"disp": "FOO > MCB", "kind": "general"}})
        self.assertEqual([{"circuit": "X-1", "token": "FOO"}], m["unmapped"])

    def test_no_values_and_cable_ref_is_a_tag(self):
        m = DM.build_board_model("TS1", self.CIRCUITS, {"M-01": "W-M01"})
        ext = [w for w in m["wires"] if w["zone"] == "external"]
        self.assertIn("W-M01", {w["cable_ref"] for w in ext})
        for w in m["wires"]:
            self.assertEqual({"id", "from", "to", "zone", "cable_ref"}, set(w))

    def test_cli_writes_one_folder_per_board(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in.json"
            src.write_text(json.dumps({"boards": {"TS1": {"circuits": {"M-01": {"disp": "MCB > KM", "kind": "motor"}}}, "TS2": {"circuits": {"IUG-01": {"kind": "lighting"}}}}}), encoding="utf-8")
            self.assertEqual(0, DM.main(["--input", str(src), "--out", str(Path(tmp) / "out")]))
            for board in ("TS1", "TS2"):
                for name in ("devices", "loads", "wires", "circuits"):
                    self.assertEqual(board, json.loads((Path(tmp) / "out" / board / f"{name}.json").read_text(encoding="utf-8"))["board"])


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


class Stage8Model(unittest.TestCase):
    """Stage 8 hands over the board model built from the calculation: chain from `disp`, kind from the circuit type, parent from `padre`; no values."""

    def test_board_model_from_the_chain(self):
        sys.path.insert(0, str(H / "src"))
        from disciplines.electrical_lv.stages.cable_list import board_diagram_model
        ch = {"form": {"board": {"name": "TS1"}}, "calc": {
            "datos": {"G-02": {"disp": "RCCB 4P 63 A 30 mA"}, "IUG-01": {"disp": "MCB (10 A)"}, "M-01": {"disp": "MCB > KM > OL (25 A)"}},
            "detalle": {"G-02": {"tipo": "seccional", "padre": ""}, "IUG-01": {"tipo": "iluminacion", "padre": "G-02"}, "M-01": {"tipo": "motor", "padre": ""}}}}
        m = board_diagram_model(ch)
        self.assertEqual("TS1", m["board"])
        self.assertEqual(["dev-TS1-bus", "dev-G-02-rccb", "dev-IUG-01-mcb", "dev-M-01-mcb", "dev-M-01-contactor", "dev-M-01-thermal_overload_relay"], [d["id"] for d in m["devices"]])
        self.assertEqual([], m["unmapped"])
        w = next(x for x in m["wires"] if x["id"] == "wire-IUG-01-load")
        self.assertEqual(("external", "IUG-01"), (w["zone"], w["cable_ref"]))
        self.assertEqual(m, board_diagram_model(ch))
