"""Tests of the bill-of-quantities engine: pure functions, small synthetic circuits."""
import copy
import unittest

import epc_boq
from epc_boq import build_boq, inputs, render_rows


def circuit(tag, **changes):
    base = {"tag": tag, "phases": 1, "s_mm2": 2.5, "neutral_mm2": 2.5, "pe_mm2": 2.5, "length_m": 10.0, "material": "cu", "insulation": "pvc",
            "device_kind": "mcb", "in_a": 16, "poles": 2, "breaking_capacity_ka": 6}
    base.update(changes)
    return base


def boq(circuits=None, **kw):
    kw.setdefault("allowance_pct", 0)
    return build_boq("TG-1", circuits if circuits is not None else [circuit("A"), circuit("B")], **kw)


def by_cat(result, category):
    return [i for i in result["items"] if i["category"] == category]


class AllowanceTests(unittest.TestCase):
    def test_required(self):
        with self.assertRaisesRegex(ValueError, "allowance_pct is required"):
            build_boq("TG-1", [circuit("A")])

    def test_zero_allowed(self):
        self.assertEqual(by_cat(boq([circuit("A")]), "cable")[0]["quantity"], 10.0)

    def test_negative_and_invalid_rejected(self):
        for bad in (-1, float("nan"), "10", True):
            with self.assertRaisesRegex(ValueError, "allowance_pct must be"):
                boq(allowance_pct=bad)

    def test_applied(self):
        cable = by_cat(boq(allowance_pct=10), "cable")[0]
        self.assertEqual(cable["quantity"], 22.0)
        self.assertIn("(20 m) x (1 + 10 %)", cable["basis"])

    def test_round_up_flag(self):
        circuits = [circuit("A", length_m=10.3)]
        self.assertEqual(by_cat(boq(circuits, allowance_pct=5), "cable")[0]["quantity"], 10.815)
        up = by_cat(boq(circuits, allowance_pct=5, round_up_m=True), "cable")[0]
        self.assertEqual(up["quantity"], 11)
        self.assertIn("rounded up", up["basis"])
        self.assertEqual(by_cat(boq([circuit("A", length_m=10)], round_up_m=True), "cable")[0]["quantity"], 10)

    def test_round_up_must_be_boolean(self):
        with self.assertRaisesRegex(ValueError, "round_up_m"):
            boq(round_up_m=1)


class CableTests(unittest.TestCase):
    def test_same_spec_is_aggregated(self):
        result = boq([circuit("B", length_m=5), circuit("A", length_m=7.5)])
        cables = by_cat(result, "cable")
        self.assertEqual(len(cables), 1)
        self.assertEqual((cables[0]["quantity"], cables[0]["unit"], cables[0]["source"]), (12.5, "m", ["A", "B"]))
        self.assertEqual(cables[0]["description"], "Cu PVC cable 1x2.5 mm2 + N 2.5 mm2 + PE 2.5 mm2 (3 cores)")
        self.assertEqual(result["totals"]["cable_m"], 12.5)

    def test_different_specs_are_separate_and_sorted(self):
        result = boq([circuit("A", s_mm2=10, phases=3), circuit("B", material="al"), circuit("C"), circuit("D", insulation="xlpe"),
                      circuit("E", neutral_mm2=None, pe_mm2=None)])
        cables = by_cat(result, "cable")
        self.assertEqual([c["item_id"] for c in cables], [f"CAB-00{n}" for n in range(1, 6)])
        self.assertEqual([c["source"] for c in cables], [["B"], ["E"], ["C"], ["A"], ["D"]])
        self.assertEqual(cables[1]["description"], "Cu PVC cable 1x2.5 mm2 (1 cores)")
        self.assertEqual(cables[3]["spec"]["cores"], 5)

    def test_missing_fields_become_issues(self):
        result = boq([circuit("A", material=None, insulation=None), circuit("B", length_m=None), circuit("C", length_m=None, material=None)])
        self.assertIn("A: missing material", result["issues"])
        self.assertIn("A: missing insulation", result["issues"])
        self.assertIn("B: missing length_m (circuit not counted)", result["issues"])
        unspecified = [c for c in by_cat(result, "cable") if "A" in c["source"]][0]
        self.assertEqual(unspecified["description"], "material unspecified insulation unspecified cable 1x2.5 mm2 + N 2.5 mm2 + PE 2.5 mm2 (3 cores)")
        self.assertEqual(unspecified["issues"], ["A: missing material", "A: missing insulation"])
        counted = [c for c in by_cat(result, "cable") if "B" in c["source"] or "C" in c["source"]]
        self.assertEqual(counted, [])

    def test_all_lengths_missing_gives_no_line(self):
        result = boq([circuit("A", length_m=None)])
        self.assertEqual(by_cat(result, "cable"), [])
        self.assertEqual(result["totals"]["cable_m"], 0)

    def test_input_order_does_not_change_the_bill(self):
        circuits = [circuit("A", s_mm2=4), circuit("B"), circuit("C", in_a=32)]
        self.assertEqual(boq(circuits), boq(list(reversed(circuits))))


class DeviceTests(unittest.TestCase):
    def test_counts_per_kind_current_poles_and_capacity(self):
        result = boq([circuit("A"), circuit("B"), circuit("C", in_a=25), circuit("D", poles=4), circuit("E", breaking_capacity_ka=10), circuit("F", device_kind="MCCB")])
        devices = by_cat(result, "protective_device")
        self.assertEqual(sorted(d["quantity"] for d in devices), [1, 1, 1, 1, 2])
        self.assertEqual(sum(d["quantity"] for d in devices), 6)
        first = devices[0]
        self.assertEqual((first["item_id"], first["unit"]), ("DEV-001", "un"))
        pair = [d for d in devices if d["quantity"] == 2][0]
        self.assertEqual((pair["source"], pair["description"]), (["A", "B"], "MCB protective device, 16 A, 2 poles, 6 kA breaking capacity"))
        self.assertEqual(result["totals"]["devices"], 6)
        self.assertEqual(devices[-1]["spec"]["kind"], "mccb")

    def test_missing_device_data(self):
        result = boq([circuit("A", device_kind=None, in_a=None, poles=None, breaking_capacity_ka=None), circuit("B", in_a=None),
                      circuit("C", device_kind=None, poles=None, breaking_capacity_ka=None)])
        self.assertIn("A: missing device", result["issues"])
        self.assertIn("B: missing in_a", result["issues"])
        self.assertIn("C: missing device_kind", result["issues"])
        devices = by_cat(result, "protective_device")
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[1]["description"], "unspecified-kind protective device, 16 A, poles unspecified, breaking capacity unspecified")
        self.assertEqual(devices[0]["description"], "MCB protective device, rated current unspecified, 2 poles, 6 kA breaking capacity")
        self.assertEqual(devices[0]["issues"], ["B: missing in_a"])


class TerminalAndEnclosureTests(unittest.TestCase):
    def test_terminal_totals_passthrough(self):
        result = boq(terminal_totals={"terminals": 9, "by_terminal_size": {"2.5": 6, "10": 3, "4": 0}})
        terminals = by_cat(result, "terminal_block")
        self.assertEqual([(t["item_id"], t["description"], t["quantity"], t["unit"]) for t in terminals],
                         [("TRM-001", "Terminal block, 2.5 mm2", 6, "un"), ("TRM-002", "Terminal block, 10 mm2", 3, "un")])
        self.assertNotIn("terminal blocks are not included: no terminal-block totals were given", result["assumptions"])

    def test_whole_terminal_list_and_none_size(self):
        result = boq(terminal_totals={"totals": {"by_terminal_size": {"2.5": 2, "none": 3}}})
        self.assertEqual(len(by_cat(result, "terminal_block")), 1)
        self.assertIn("3 terminal(s) have no assigned terminal size (not counted)", result["issues"])

    def test_without_terminal_totals(self):
        result = boq()
        self.assertEqual(by_cat(result, "terminal_block"), [])
        self.assertIn("terminal blocks are not included: no terminal-block totals were given", result["assumptions"])

    def test_invalid_terminal_totals(self):
        for bad, message in ((5, "must be an object"), ({"x": 1}, "by_terminal_size"), ({"by_terminal_size": {"2.5": -1}}, "integer >= 0"),
                             ({"by_terminal_size": {"2.5": True}}, "integer >= 0"), ({"by_terminal_size": {"abc": 1}}, "not a number"),
                             ({"by_terminal_size": {"-4": 1}}, "positive"), ({"totals": 3}, "by_terminal_size")):
            with self.assertRaisesRegex(ValueError, message):
                boq(terminal_totals=bad)

    def test_one_enclosure_per_board(self):
        enclosure = by_cat(boq(), "enclosure")
        self.assertEqual(len(enclosure), 1)
        self.assertEqual((enclosure[0]["item_id"], enclosure[0]["quantity"], enclosure[0]["unit"], enclosure[0]["source"]), ("ENC-001", 1, "un", ["A", "B"]))
        self.assertIn("TG-1", enclosure[0]["description"])


class ResultTests(unittest.TestCase):
    def test_shape_totals_and_no_prices(self):
        result = boq(terminal_totals={"by_terminal_size": {"2.5": 1}})
        self.assertEqual(set(result), {"board", "allowance_pct", "round_up_m", "items", "totals", "assumptions", "norm_records", "issues"})
        self.assertEqual(result["norm_records"], [])
        self.assertEqual(result["totals"]["lines"], len(result["items"]))
        self.assertEqual([i["category"] for i in result["items"]], ["cable", "protective_device", "terminal_block", "enclosure"])
        for item in result["items"]:
            self.assertEqual(set(item), {"item_id", "category", "description", "unit", "quantity", "source", "basis", "spec", "issues"})
            self.assertFalse({"price", "cost"} & set(item))
        self.assertEqual(len({i["item_id"] for i in result["items"]}), len(result["items"]))

    def test_deterministic_and_input_not_modified(self):
        circuits = [circuit("A"), circuit("B", s_mm2=6)]
        before = copy.deepcopy(circuits)
        self.assertEqual(boq(circuits), boq(circuits))
        self.assertEqual(circuits, before)

    def test_render_rows(self):
        rows = render_rows(boq([circuit("A", material=None)]))
        self.assertEqual([r["item_id"] for r in rows], ["CAB-001", "DEV-001", "ENC-001"])
        self.assertEqual(set(rows[0]), {"board", "item_id", "category", "description", "unit", "quantity", "source", "basis", "issue"})
        self.assertEqual(rows[0]["issue"], "A: missing material")
        self.assertEqual(rows[2]["source"], "A")

    def test_package_exports(self):
        self.assertEqual(sorted(epc_boq.__all__), ["BoqError", "build_boq", "render_rows"])
        self.assertEqual(epc_boq.__version__, "0.1.0")

    def test_public_door(self):
        """COD-02: `epc_boq.api` offers exactly what the package exports."""
        import importlib
        api = importlib.import_module("epc_boq.api")
        self.assertEqual(sorted(api.__all__), sorted(epc_boq.__all__))
        for name in api.__all__:
            self.assertIs(getattr(api, name), getattr(epc_boq, name))


class ValidationTests(unittest.TestCase):
    def check(self, circuits, message, **kw):
        with self.assertRaisesRegex(ValueError, message):
            boq(circuits, **kw)

    def test_circuits(self):
        self.check([], "non-empty list")
        self.check("x", "non-empty list")
        self.check([5], "must be an object")
        self.check([{"tag": "A", "phases": 1, "s_mm2": 1, "bogus": 1}], "unknown key")
        self.check([circuit("A"), circuit("A")], "duplicate circuit tag")
        self.check([circuit("")], "tag must be")
        self.check([circuit("A", phases=2)], "phases must be")
        self.check([circuit("A", phases=True)], "phases must be")
        self.check([circuit("A", s_mm2=0)], "s_mm2 must be")
        self.check([circuit("A", s_mm2=None)], "s_mm2 must be")
        self.check([circuit("A", length_m=-3)], "length_m must be")
        self.check([circuit("A", in_a=float("inf"))], "in_a must be")
        self.check([circuit("A", material="")], "material must be")
        self.check([circuit("A", poles=5)], "poles must be")
        self.check([circuit("A", poles=True)], "poles must be")

    def test_board_name(self):
        with self.assertRaisesRegex(ValueError, "board_name"):
            build_boq(" ", [circuit("A")], allowance_pct=0)

    def test_text_is_normalised(self):
        cable = by_cat(boq([circuit("A", material=" CU ", insulation="Pvc")]), "cable")[0]
        self.assertEqual((cable["spec"]["material"], cable["spec"]["insulation"]), ("cu", "pvc"))

    def test_inputs_helpers(self):
        self.assertIsNone(inputs.number(None, "x", True))
        self.assertEqual(inputs.terminal_totals(None), {})


if __name__ == "__main__":
    unittest.main()


class EquipmentTests(unittest.TestCase):
    def test_equipment_counted_by_another_engine_becomes_numbered_lines(self):
        lines = [{"description": "PV module, array A1", "unit": "un", "quantity": 210, "source": ["A1"]}, {"description": "PV inverter, array A1", "quantity": 1}]
        result = boq(equipment=lines)
        found = by_cat(result, "pv_equipment")
        self.assertEqual([i["item_id"] for i in found], ["PVE-001", "PVE-002"])
        self.assertEqual([i["quantity"] for i in found], [210, 1])
        self.assertEqual(found[1]["unit"], "un")
        self.assertEqual(by_cat(boq(), "pv_equipment"), [])

    def test_tray_system_lines_are_numbered_apart_from_the_plant_ones(self):
        result = boq(equipment=[{"description": "Tray BN-ESC-300x90", "unit": "m", "quantity": 12.5, "category": "tray_system"}, {"description": "PV module", "quantity": 4}])
        self.assertEqual([i["item_id"] for i in by_cat(result, "tray_system")], ["BAN-001"])
        self.assertIn("take-off", by_cat(result, "tray_system")[0]["basis"])
        self.assertEqual([i["item_id"] for i in by_cat(result, "pv_equipment")], ["PVE-001"])
        with self.assertRaises(ValueError):
            boq(equipment=[{"description": "x", "quantity": 1, "category": "cable"}])

    def test_a_bad_equipment_line_is_refused(self):
        for bad in ({"description": "", "quantity": 1}, {"description": "x", "quantity": -1}, {"description": "x", "quantity": True}, "x"):
            with self.assertRaises(ValueError):
                boq(equipment=[bad])
