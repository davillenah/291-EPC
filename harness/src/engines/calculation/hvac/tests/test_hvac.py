"""The cooling load: each formula, the pipeline, the contract and the CLI."""
import json
import tempfile
import unittest
from pathlib import Path

from epc_hvac import HvacError, __main__ as cli, config, loads, run

DOC = {"design": {"t_out_c": 35, "t_in_c": 24, "w_out_kg_kg": 0.018, "w_in_kg_kg": 0.0093, "supply_delta_t_k": 10},
       "spaces": [{"id": "S1", "name": "Office", "area_m2": 50, "height_m": 3, "use": "office", "occupants": 10, "lighting_w_m2": 10, "equipment_w_m2": 15,
                   "envelope": [{"kind": "wall", "area_m2": 30, "u_w_m2k": 0.5}, {"kind": "window", "area_m2": 6, "u_w_m2k": 2.8, "shgc": 0.4, "orientation": "W"}]}]}
SCHEMAS = Path(__file__).resolve().parents[1] / "src" / "epc_hvac" / "schema"


class TestFormulas(unittest.TestCase):
    def test_each_heat_flow(self):
        self.assertAlmostEqual(loads.conduction_w(0.5, 30, 11), 165.0)
        self.assertAlmostEqual(loads.solar_w(6, 0.4, "W"), 6 * 0.4 * 500)
        self.assertEqual(loads.people_w(10), {"sensible": 750, "latent": 550})
        self.assertEqual(loads.internal_w(50, 10), 500)
        a = loads.air_w(100, 10, 0.005)
        self.assertAlmostEqual(a["sensible"], 1230.0)
        self.assertAlmostEqual(a["latent"], 3010 * 100 * 0.005)
        self.assertAlmostEqual(loads.infiltration_ls(150, 0.3), 12.5)

    def test_the_ventilation_and_the_supply_air(self):
        self.assertAlmostEqual(loads.ventilation_ls("office", 10, 50), 10 * 2.5 + 50 * 0.3)
        self.assertEqual(loads.ventilation_ls("unknown use", 10, 50), loads.ventilation_ls("default", 10, 50))
        self.assertAlmostEqual(loads.supply_flow_ls(1230, 10), 100.0)
        self.assertEqual(loads.supply_flow_ls(-5, 10), 0.0)
        self.assertAlmostEqual(loads.refrigeration_tons(3516.85), 1.0)

    def test_bad_values_are_refused(self):
        for call in (lambda: loads.conduction_w(-1, 1, 1), lambda: loads.solar_w(1, 2, "N"), lambda: loads.solar_w(1, 0.4, "X"), lambda: loads.supply_flow_ls(100, 0)):
            with self.assertRaises(HvacError):
                call()


class TestPipeline(unittest.TestCase):
    def test_a_space_is_the_sum_of_its_parts(self):
        r = run(DOC).as_dict()
        s = r["spaces"][0]
        self.assertEqual(s["id"], "S1")
        self.assertAlmostEqual(sum(s["parts_w"].values()), s["total_w"], delta=1.0)
        self.assertGreater(s["supply_ls"], 0)
        self.assertEqual(r["totals"]["total_w"], s["total_w"])
        self.assertTrue(r["warnings"])                                  # typical values: it says so

    def test_the_input_is_checked_and_can_be_text(self):
        self.assertEqual(run(json.dumps(DOC)).as_dict()["counts"], {"spaces": 1})
        self.assertEqual(run(json.dumps(DOC).encode()).as_dict()["counts"], {"spaces": 1})
        for bad in ("not json", {}, {"design": DOC["design"], "spaces": [{"id": "x"}]}, {"spaces": DOC["spaces"]}):
            with self.assertRaises(HvacError):
                run(bad)

    def test_more_people_need_more(self):
        more = json.loads(json.dumps(DOC))
        more["spaces"][0]["occupants"] = 30
        self.assertGreater(run(more).totals["total_w"], run(DOC).totals["total_w"])


class TestContract(unittest.TestCase):
    def test_schemas_accept_the_example_and_its_result(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        jsonschema.validate(DOC, json.loads((SCHEMAS / "input.schema.json").read_text(encoding="utf-8")))
        jsonschema.validate(run(DOC).as_dict(), json.loads((SCHEMAS / "output.schema.json").read_text(encoding="utf-8")))

    def test_the_cli_writes_inside_out_and_reports_errors(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "in.json"
            src.write_text(json.dumps(DOC), encoding="utf-8")
            self.assertEqual(cli.main([str(src), "--out", str(Path(d) / "out")]), 0)
            self.assertTrue((Path(d) / "out" / "hvac_loads.json").is_file())
            src.write_text("{}", encoding="utf-8")
            self.assertEqual(cli.main([str(src), "--out", str(Path(d) / "out")]), 1)

    def test_the_typical_values_are_in_one_file_sectioned_for_the_norms_page(self):
        data = config.typical()
        self.assertEqual(sorted(k for k in data if not k.startswith("_")), ["params", "solar", "ventilation"])
        self.assertIn("default", data["ventilation"])


if __name__ == "__main__":
    unittest.main()
