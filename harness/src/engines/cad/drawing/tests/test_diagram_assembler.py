"""The relational diagram model, the design constraints and the four-source assembler (ADR-0037), covered inside the engine's own suite."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from epc_drawing import diagram_assembler as A   # noqa: E402
from epc_drawing import diagram_knowledge as K   # noqa: E402
from epc_drawing import diagram_model as DM      # noqa: E402

CIRCUITS = {"G-02": {"disp": "RCCB 4P 63 A 30 mA", "kind": "feeder"}, "IUG-01": {"disp": "MCB (10 A)", "kind": "lighting", "parent": "G-02"},
            "M-01": {"disp": "MCB > KM > OL (25 A)", "kind": "motor"}, "T-01": {"kind": "sockets"}}


class ModelAndAssembler(unittest.TestCase):
    def test_model_is_deterministic_and_children_hang_from_the_parent(self):
        a = DM.build_board_model("TS1", CIRCUITS)
        self.assertEqual(a, DM.build_board_model("TS1", dict(reversed(list(CIRCUITS.items())))))
        first = next(w for w in a["wires"] if w["id"] == "wire-IUG-01-1")
        self.assertEqual("dev-G-02-rccb", first["from"]["ref"])
        self.assertEqual([], a["unmapped"])

    def test_assembly_passes_values_and_cable_rows_through(self):
        m = DM.build_board_model("TS1", CIRCUITS)
        rows = [{"circuit": "IUG-01", "length_m": 18}]
        a = A.assemble(dict(m, board="TS1"), {"IUG-01": {"in_a": 10, "icu_ka": 6, "du_pct": 1.2}}, rows)
        c = next(x for x in a["circuits"] if x["tag"] == "IUG-01")
        self.assertEqual(["dev-IUG-01-mcb"], [d["id"] for d in c["devices"]])
        self.assertEqual((10, 6), (c["devices"][0]["labels"]["rated_current"], c["devices"][0]["labels"]["breaking_capacity"]))
        self.assertEqual(rows[0], next(w for w in c["wires"] if w["zone"] == "external")["cable"])
        self.assertEqual([], a["violations"])

    def test_missing_data_is_none_not_invented(self):
        m = DM.build_board_model("TS1", {"X-1": {"disp": "MCB", "kind": "general"}})
        c = A.assemble(dict(m, board="TS1"), {}, [])["circuits"][0]
        self.assertEqual({"tag": "-X-1.1"}, c["devices"][0]["labels"])
        self.assertIsNone(next(w for w in c["wires"] if w["zone"] == "external")["cable"])

    def test_constraints(self):
        bad = DM.build_board_model("TS1", {"G-1": {"disp": "RCCB 2P 40 A 30 mA", "kind": "feeder"}, "L-1": {"disp": "MCB 4P (10 A)", "kind": "lighting", "parent": "G-1"}})
        self.assertEqual(["dc-01"], [v["constraint"] for v in K.check_constraints(bad)])
        unknown = DM.build_board_model("TS1", {"G-1": {"disp": "RCCB 40 A", "kind": "feeder"}, "L-1": {"disp": "MCB 4P (10 A)", "kind": "lighting", "parent": "G-1"}})
        self.assertEqual([], K.check_constraints(unknown))
        m = DM.build_board_model("TS1", {"M-1": {"disp": "MCB > KM", "kind": "motor"}})
        self.assertEqual(["dc-02"], [v["constraint"] for v in K.check_constraints(m)])
        a = A.assemble(dict(m, board="TS1"), {}, [], symbols=lambda d: {"sld_symbol": "X-" + d})
        self.assertEqual("X-mcb", a["circuits"][0]["devices"][0]["symbol"])
        self.assertIn("id", a["circuits"][0]["devices"][0]["iec_60617"])

    def test_typical_topologies_build(self):
        m = DM.build_board_model("TS1", {"M-02": {"kind": "motor_star_delta"}, "A-01": {"kind": "ats_feeder"}, "MV-01": {"kind": "mv_intake"}})
        self.assertEqual([], m["unmapped"])

    def test_structured_chain_wins_over_the_text(self):
        chain = [{"symbol": "lv_mcb", "short": "MCB", "poles": 3}, {"symbol": "lv_contactor", "short": "KM", "poles": 3}]
        m = DM.build_board_model("TS1", {"M-1": {"chain": chain, "disp": "MCCB (10 A)", "kind": "motor"}})
        self.assertEqual(["dev-M-1-mcb", "dev-M-1-contactor"], [d["id"] for d in m["devices"] if d["id"] != "dev-TS1-bus"])
        self.assertEqual([3, 3], [d["poles"] for d in m["devices"] if "poles" in d])
        self.assertEqual([], m["unmapped"])

    def test_structured_chain_reports_what_it_cannot_map(self):
        m = DM.build_board_model("TS1", {"M-1": {"chain": [{"symbol": "lv_vfd", "short": "VFD", "poles": 3}], "kind": "motor"}})
        self.assertEqual([{"circuit": "M-1", "token": "VFD"}], m["unmapped"])


if __name__ == "__main__":
    unittest.main()
