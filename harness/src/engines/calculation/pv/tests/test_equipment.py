"""The equipment data (`epc_pv.equipment`): every record is read, the inverter blocks follow the data sheets, nothing is made up, and the foundation of a structure comes from its record."""
import json
import unittest
from pathlib import Path

from epc_pv import catalog, equipment, layout as lay
from epc_pv.model import PvError

DATA = Path(equipment.__file__).parent / "data"


def required(schema_file, record):
    schema = json.loads((DATA / schema_file).read_text(encoding="utf-8"))
    return [k for k in schema["required"] if k not in record]


class TestRecordsAreRead(unittest.TestCase):
    def test_every_json_of_the_data_folder_is_read_by_the_engine(self):
        self.assertEqual(len(equipment.inverter_records()), 10)
        self.assertEqual(len(equipment.accessories()), 25)
        self.assertEqual(len(equipment.module_technologies()), 13)
        self.assertEqual(len(equipment.module_formats()), 14)
        self.assertEqual(len(equipment.structures("ground")), 10)
        self.assertEqual(len(equipment.structures("roof")), 13)
        for name in equipment.REFERENCE_FILES:
            self.assertTrue(equipment.reference(name))
        with self.assertRaises(KeyError):
            equipment.reference("nope")

    def test_every_record_has_the_keys_of_its_schema(self):
        for rec in equipment.inverter_records():
            self.assertEqual(required("pv_inverters/pv_inverter.schema.json", rec), [], rec["id"])
        for rec in equipment.module_technologies() + equipment.module_formats():
            self.assertEqual(required("pv_modules/pv_module.schema.json", rec), [], rec["id"])
        for rec in equipment.structures():
            self.assertEqual(required("mounting_structures/mounting_structure.schema.json", rec), [], rec["id"])

    def test_the_data_is_packaged(self):
        text = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
        for pattern in ("data/*.json", "data/*/*.json", "data/*/*/*.json"):
            self.assertIn(f'"{pattern}"', text)


class TestInverters(unittest.TestCase):
    def test_the_blocks_agree_with_the_old_catalog_file_so_the_two_sources_cannot_drift(self):
        old = json.loads((DATA / "inverter_catalog.json").read_text(encoding="utf-8"))["inverters"]
        derived = {r["id"]: r for r in catalog.inverters()}
        for rec in old:
            self.assertEqual(derived[rec["id"]]["inverter"], rec["inverter"], rec["id"])

    def test_a_value_the_sheet_does_not_give_as_one_number_makes_the_model_unusable(self):
        ids = {r["id"] for r in catalog.inverters()}
        gaps = {g["id"]: g["missing"] for g in equipment.inverter_gaps()}
        self.assertNotIn("fronius.symo-advanced-20-0-3-m", ids)
        self.assertEqual(gaps["fronius.symo-advanced-20-0-3-m"], ["i_max_input_a"])       # "33.0 or 27.0 (ambiguous)"
        self.assertIn("pac0_w", gaps["sungrow.sg110cx"])                                    # only kVA: active power not stated
        self.assertEqual(len(ids) + len(gaps), 16)

    def test_the_pick_keeps_to_inverters_that_admit_a_string_of_the_module(self):
        module = {"pmax_w": 560, "voc_v": 50.99, "vmp_v": 42.82, "isc_a": 13.89, "imp_a": 13.08, "beta_voc_pct_c": -0.23, "gamma_pmax_pct_c": -0.28}
        rec = catalog.pick_inverter(500, 560, 1.2, module=module)
        self.assertIn(rec["id"], {r["id"] for r in catalog.inverters()})

    def test_the_pick_never_takes_an_input_that_cannot_carry_one_string(self):
        module = {"pmax_w": 720, "voc_v": 49.5, "vmp_v": 41.5, "isc_a": 18.5, "imp_a": 17.3, "beta_voc_pct_c": -0.25, "gamma_pmax_pct_c": -0.29}
        for n in (8, 48, 500):
            rec = catalog.pick_inverter(n, 720, 1.2, module=module)
            self.assertGreaterEqual(rec["inverter"]["i_max_input_a"], module["imp_a"])


class TestMore(unittest.TestCase):
    def test_accessories_and_missing_ids(self):
        first = equipment.accessories()[0]
        self.assertEqual(equipment.accessory(first["id"]), first)
        for call in (equipment.accessory, equipment.structure):
            with self.assertRaises(KeyError):
                call("nope")

    def test_a_power_in_kva_is_not_active_power_and_a_range_with_two_meanings_is_a_gap(self):
        self.assertIsNone(equipment._power_w({"rated_ac_power_kva": 110}))
        self.assertIsNone(equipment._window("200-1000 full; 550-850 nominal"))
        self.assertEqual(equipment._window("200-800 (usable MPP 80-800)"), (200.0, 800.0))
        rec = {"name": {"en": "X"}, "electrical_ratings": {"rated_ac_power_by_model_kw": {"A": 5}, "mppt_voltage_range_v": "100-500"}}
        self.assertEqual(equipment._models(rec), [("A", 5000.0, "100-500")])      # one window for every model
        self.assertIsNone(equipment.module_format([1, 1]))
        self.assertIsNone(equipment.module_weight_kg([1, 1]))
        self.assertIsNotNone(equipment.module_weight_kg(equipment.module_formats()[0]["geometry"]["module_dimensions_mm"]))


class TestStructures(unittest.TestCase):
    def test_the_depth_is_the_one_the_record_states_and_never_assumed(self):
        pile = equipment.foundation("driven_pile_fixed_table")
        self.assertEqual((pile["kind"], pile["embedment_m"]), ("embedded", 1.5))
        self.assertIsNone(equipment.foundation("ground_screw_fixed_table")["embedment_m"])
        self.assertIsNone(equipment.foundation("roof_flat_slab_anchored")["embedment_m"])
        self.assertEqual(equipment.foundation("roof_flat_ballast_tilted_frame")["kind"], "ballast")

    def test_a_layout_carries_the_foundation_and_refuses_the_wrong_family(self):
        base = {"site": {"width_m": 40, "length_m": 30, "setback_m": 2}, "module_dimensions_mm": [2278, 1134], "module_gap_m": 0.02, "table": {"rows": 2, "modules_per_row": 4, "orientation": "portrait"},
                "table_gap_m": 0.5, "road_width_m": 4, "station": {"width_m": 6, "depth_m": 2.5}, "inverter_pad": {"width_m": 0.7, "depth_m": 0.4}}
        lay.check(dict(base, structure_id="driven_pile_fixed_table"))
        with self.assertRaises(PvError):
            lay.check(dict(base, structure_id="roof_flat_slab_anchored"))
        with self.assertRaises(PvError):
            lay.check(dict(base, structure_id="no_such_structure"))


class TestPlantFoundation(unittest.TestCase):
    LAYOUT = {"site": {"width_m": 40, "length_m": 30, "setback_m": 2}, "module_dimensions_mm": [2278, 1134], "module_gap_m": 0.02, "table": {"rows": 2, "modules_per_row": 4, "orientation": "portrait"},
              "table_gap_m": 0.5, "road_width_m": 4, "station": {"width_m": 6, "depth_m": 2.5}, "inverter_pad": {"width_m": 0.7, "depth_m": 0.4}, "front_clearance_m": 0.5}

    def codes(self, structure_id):
        from epc_pv import flatroof
        spec = flatroof.spec_from_layout(dict(self.LAYOUT, structure_id=structure_id), {"module": {}, "inverter": {}})
        self.assertEqual(spec["structure_id"], structure_id)
        found = lay._structure(flat_layout(spec))
        return [w["code"] for w in lay._foundation_warnings(found)]

    def test_a_stated_depth_is_pending_review_and_a_missing_depth_of_piles_is_said(self):
        self.assertEqual(self.codes("driven_pile_fixed_table"), ["foundation_unverified"])
        self.assertEqual(self.codes("ground_screw_fixed_table"), ["foundation_depth_not_found"])
        self.assertEqual(lay._foundation_warnings(None), [])


def flat_layout(spec):
    from epc_pv import flatroof
    return flatroof._layout(spec)


class TestModules(unittest.TestCase):
    def test_a_catalog_module_finds_its_format(self):
        rec = next(r for r in catalog.module_records() if r.get("dimensions_mm") and r["dimensions_mm"][:2] == [2278, 1134])
        self.assertIsNotNone(equipment.module_format(rec["dimensions_mm"]))


if __name__ == "__main__":
    unittest.main()
