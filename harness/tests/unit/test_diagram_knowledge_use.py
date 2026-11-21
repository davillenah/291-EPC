"""epc_drawing.diagram_knowledge: rule evaluation, symbol lookup and the advisory board cross-check (it never changes a result)."""
import json
import sys
import unittest
import unittest.mock
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


class DiagramAssembly(unittest.TestCase):
    """The assembler joins the model (connections), the calculation values and the cable-list rows; the stage hands it over from the calculation. Nothing is computed."""

    CH = {"form": {"board": {"name": "TS1"}}, "calc": {
        "datos": {"G-02": {"disp": "RCCB 4P 63 A 30 mA", "In": 63}, "IUG-01": {"disp": "MCB (10 A)", "In": 10, "S": 1.5, "dU": 1.2, "icu": 6}, "M-01": {"disp": "MCB > KM > OL (25 A)", "In": 25}},
        "detalle": {"G-02": {"tipo": "seccional", "padre": ""}, "IUG-01": {"tipo": "iluminacion", "padre": "G-02", "ib_a": 7.5}, "M-01": {"tipo": "motor", "padre": ""}}}}

    def test_assembly_from_the_calculation(self):
        sys.path.insert(0, str(H / "src"))
        from disciplines.electrical_lv.stages import cable_list
        rows = [{"circuit": "IUG-01", "length_m": 18, "s_mm2": 1.5}]
        with unittest.mock.patch.object(cable_list, "cable_rows", return_value=rows):
            a = cable_list.board_diagram_assembly(self.CH, [])
            again = cable_list.board_diagram_assembly(self.CH, [])
        self.assertEqual(a, again)
        self.assertEqual("TS1", a["board"])
        self.assertEqual([], a["unmapped"])
        c = next(x for x in a["circuits"] if x["tag"] == "IUG-01")
        self.assertEqual(["dev-IUG-01-mcb"], [d["id"] for d in c["devices"]])
        self.assertEqual(("lv_mcb", 10, 6), (c["devices"][0]["symbol"], c["devices"][0]["labels"]["rated_current"], c["devices"][0]["labels"]["breaking_capacity"]))
        w = next(x for x in c["wires"] if x["zone"] == "external")
        self.assertEqual(rows[0], w["cable"])
        self.assertEqual(1.2, c["values"]["du_pct"])

    def test_a_missing_cable_row_is_none_and_no_values_are_invented(self):
        from epc_drawing import diagram_assembler as A
        m = DM.build_board_model("TS1", {"X-1": {"disp": "MCB", "kind": "general"}})
        a = A.assemble(dict(m, board="TS1"), {}, [], verdict=K.audit(m))
        c = a["circuits"][0]
        self.assertEqual({"tag": "-X-1.1"}, c["devices"][0]["labels"])
        self.assertIsNone(next(w for w in c["wires"] if w["zone"] == "external")["cable"])


class SolutionChainFeedsTheNetlist(unittest.TestCase):
    """The netlist reads the structured chain of the standard solution (`detalle.cadena`), not the text; the result equals the one read from the text."""

    def test_chain_and_text_give_the_same_devices(self):
        from epc_aea90364 import solutions as S
        cases = [("G-02", "feeder", "feeder", "3F+N", "seccional", 63, 50, True, False), ("M-01", "motor", "dol", "3F", "motor", 25, 20, False, True)]
        for tag, kind, top, phase, tipo, in_a, ib, kids, motor in cases:
            sol = S.resolve(S.facts(tag, "", "", top, kind, phase, tipo, in_a, ib, 10, 30, kids, motor))
            by_chain = DM.build_board_model("TS1", {tag: {"chain": sol["chain"], "kind": kind}})
            by_text = DM.build_board_model("TS1", {tag: {"disp": sol["disp"], "kind": kind}})
            self.assertEqual([d["id"] for d in by_text["devices"]], [d["id"] for d in by_chain["devices"]], tag)
            self.assertEqual(by_text["unmapped"], by_chain["unmapped"], tag)


class DesignConstraints(unittest.TestCase):
    """Design rules are constraints on the connections (no 4P MCB behind a 2P RCCB), not symbols; a constraint without its data is not applied."""

    def test_poles_behind_an_rccb(self):
        bad = DM.build_board_model("TS1", {"G-1": {"disp": "RCCB 2P 40 A 30 mA", "kind": "feeder"}, "L-1": {"disp": "MCB 4P (10 A)", "kind": "lighting", "parent": "G-1"}})
        self.assertEqual([2, 4], [d["poles"] for d in bad["devices"] if "poles" in d])
        found = K.check_constraints(bad)
        self.assertEqual([("dc-01", "dev-L-1-mcb", "dev-G-1-rccb")], [(v["constraint"], v["device"], v["upstream"]) for v in found])
        self.assertEqual("major", found[0]["severity"])
        ok = DM.build_board_model("TS1", {"G-1": {"disp": "RCCB 4P 40 A 30 mA", "kind": "feeder"}, "L-1": {"disp": "MCB 2P (10 A)", "kind": "lighting", "parent": "G-1"}})
        self.assertEqual([], K.check_constraints(ok))
        unknown = DM.build_board_model("TS1", {"G-1": {"disp": "RCCB 40 A", "kind": "feeder"}, "L-1": {"disp": "MCB 4P (10 A)", "kind": "lighting", "parent": "G-1"}})
        self.assertEqual([], K.check_constraints(unknown))

    def test_contactor_needs_overload_protection(self):
        m = DM.build_board_model("TS1", {"M-1": {"disp": "MCB > KM", "kind": "motor"}, "M-2": {"disp": "MCB > KM > OL (25 A)", "kind": "motor"}})
        self.assertEqual([("dc-02", "dev-M-1-contactor")], [(v["constraint"], v["device"]) for v in K.check_constraints(m)])

    def test_assembly_reports_violations_and_the_iec_reference(self):
        from epc_drawing import diagram_assembler as A
        m = dict(DM.build_board_model("TS1", {"M-1": {"disp": "MCB > KM", "kind": "motor"}}), board="TS1")
        a = A.assemble(m, {}, [], symbols=lambda d: {"sld_symbol": "X-" + d}, verdict=K.audit(m))
        self.assertEqual(["dc-02"], [v["constraint"] for v in a["violations"]])
        mcb = a["circuits"][0]["devices"][0]
        self.assertEqual("X-mcb", mcb["symbol"])
        self.assertIn("id", mcb["iec_60617"])


class TypicalTopologies(unittest.TestCase):
    """The typical chains of star-delta, ATS, UPS and the MV intake exist in the library and build a model with no unmapped device."""

    def test_new_kinds_build_with_library_symbols(self):
        topo = DM._topologies()["kinds"]
        for kind in ("motor_star_delta", "ats_feeder", "ups_feeder", "mv_intake", "mv_transformer_feeder"):
            self.assertIn(kind, topo)
            for role in topo[kind]["chain"]:
                self.assertIsNotNone(K.symbol_for(role)["sld_symbol"], f"{kind}/{role}")
        m = DM.build_board_model("TS1", {"M-02": {"kind": "motor_star_delta"}, "A-01": {"kind": "ats_feeder"}, "U-01": {"kind": "ups_feeder"}, "MV-01": {"kind": "mv_intake"}})
        self.assertEqual([], m["unmapped"])
        ids = [d["id"] for d in m["devices"]]
        self.assertEqual(3, sum(1 for i in ids if i.startswith("dev-M-02-contactor")))
        self.assertIn("dev-A-01-ats", ids)
        self.assertEqual(2, sum(1 for i in ids if i.startswith("dev-MV-01-")))
