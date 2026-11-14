"""Building intake: the recognised floors become lighting rooms and `L-<floor>` loads before stage 1 freezes the load list."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import epc_lighting as EL  # noqa: E402
import test_pipeline_wiring as W  # noqa: E402
from disciplines.electrical_lv.intake.building import BuildingError, derive  # noqa: E402
from disciplines.electrical_lv.pipeline import STAGES, run  # noqa: E402

LUM = {"id": "LED1", "lamps": 1, "lamp_flux_lm": 3600, "power_w": 36}
DATA = {"activity": "task.reading", "luminaire": "LED1", "height_m": 2.8, "coefficient_of_utilisation": 0.6}
# two rectangular rooms and an L-shaped one, as epc_arch gives them (area and the box of the rectangles in metres)
ARCH = {"rooms": [{"id": "r1", "name": "OFICINA", "area_m2": 20.0, "size_m": [4.0, 5.0]},
                  {"id": "r2", "name": "HALL", "area_m2": 12.0, "size_m": [3.0, 4.0]},
                  {"id": "r3", "name": "L", "area_m2": 16.0, "size_m": [5.0, 5.0]}]}


def building(**floor):
    f = {"id": "PB", "name": "Ground floor", "phases": 1, "length": {"value": 20, "unit": "m"}, "architecture": copy.deepcopy(ARCH),
         "rooms": {"r1": dict(DATA), "r3": dict(DATA)}, "by_name": {"HALL": dict(DATA)}}
    f.update(floor)
    return {"luminaires": [dict(LUM)], "floors": [f]}


def loads():
    return json.loads(json.dumps(W.loads_doc()))


class DeriveTests(unittest.TestCase):
    def test_the_load_power_is_the_installed_power_of_the_engine(self):
        out, section = derive(building(), loads())
        direct = EL.run(copy.deepcopy(section["document"])).as_dict()
        load = [x for x in out["loads"] if x["id"] == "L-PB"][0]
        self.assertEqual(load["power"], {"value": sum(r["energy"]["installed_power_w"] for r in direct["rooms"]), "unit": "W"})
        self.assertEqual((load["kind"], load["area"], load["phases"], load["length"]), ("lighting", "PB", 1, {"value": 20, "unit": "m"}))
        self.assertIn({"id": "PB", "name": "Ground floor"}, out["areas"])

    def test_the_room_keeps_its_area_and_the_shorter_side_is_the_width(self):
        _, section = derive(building(), loads())
        rooms = {r["id"]: r for r in section["document"]["rooms"]}
        self.assertEqual(sorted(rooms), ["PB-r1", "PB-r2", "PB-r3"])
        for rid, area in (("PB-r1", 20.0), ("PB-r2", 12.0), ("PB-r3", 16.0)):
            self.assertAlmostEqual(rooms[rid]["width_m"] * rooms[rid]["length_m"], area, places=2)
            self.assertLessEqual(rooms[rid]["width_m"], rooms[rid]["length_m"])

    def test_the_inputs_are_not_changed_and_the_loads_stay(self):
        original, b = loads(), building()
        before = (json.dumps(original, sort_keys=True), json.dumps(b, sort_keys=True))
        out, _ = derive(b, original)
        self.assertEqual((json.dumps(original, sort_keys=True), json.dumps(b, sort_keys=True)), before)
        self.assertEqual(out["loads"][:len(original["loads"])], original["loads"])

    def test_a_room_without_data_is_an_error_unless_it_is_excluded(self):
        with self.assertRaises(BuildingError) as ctx:
            derive(building(rooms={"r1": dict(DATA)}, by_name={}), loads())
        self.assertTrue(any("r2" in e and "no lighting data" in e for e in ctx.exception.errors))
        _, section = derive(building(rooms={"r1": dict(DATA)}, by_name={}, exclude=["r2", "r3"]), loads())
        self.assertEqual([r["id"] for r in section["document"]["rooms"]], ["PB-r1"])

    def test_nothing_is_defaulted(self):
        for key in ("phases", "length"):
            b = building()
            del b["floors"][0][key]
            with self.subTest(key=key), self.assertRaises(BuildingError) as ctx:
                derive(b, loads())
            self.assertIn(key, ctx.exception.errors[0])
        for key in ("activity", "luminaire", "height_m"):       # the engine may estimate or read the coefficient of utilisation itself; the rest it requires
            b = building()
            del b["floors"][0]["rooms"]["r1"][key]
            with self.subTest(room_key=key), self.assertRaises(BuildingError):
                derive(b, loads())

    def test_wrong_inputs_are_named(self):
        cases = ((building(rooms={"r1": dict(DATA, width_m=3)}), "come from the architecture"),
                 (building(exclude=["r9"]), "r9"),
                 (building(architecture={"rooms": [{"id": "r1", "name": "x", "area_m2": None, "size_m": None}]}, rooms={"r1": dict(DATA)}, by_name={}), "plan units"),
                 (dict(building(), floors=[]), "floors"))
        for b, text in cases:
            with self.subTest(text=text), self.assertRaises(BuildingError) as ctx:
                derive(b, loads())
            self.assertIn(text, "; ".join(ctx.exception.errors))
        taken = loads()
        taken["loads"][0]["id"] = "L-PB"
        with self.assertRaises(BuildingError):
            derive(building(), taken)

    def test_with_a_tolerance_stage_3_compares_the_load_with_its_rooms(self):
        b = building()
        b["tolerance_pct"] = 1
        out, section = derive(b, loads())
        inputs = W.inputs_doc()
        inputs["lighting"] = section
        ctx = W.context(engine_inputs=inputs, loads=out)
        run(ctx, stop_after=2, run_id="r3")
        res = STAGES[2].run(ctx)
        check = res.outputs["lighting"]["load_check"]
        self.assertEqual((res.status, len(check), check[0]["within_tolerance"]), ("ok", 1, True))
        self.assertEqual(check[0]["difference_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()


class ApiTests(unittest.TestCase):
    """The platform run: the load list given by the caller gets its lighting loads from the building, and stage 3 receives the lighting section."""

    def run_api(self, building_section, **extra):
        import tempfile
        import test_platform_api as A
        from epc_platform import api
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api.init_project(root, "API-1", A.ANSWERS, clock=A.CLOCK, actor=A.ORC)
            inputs = dict(W.inputs_doc(), building=building_section, **extra)
            return api.run_pipeline(root / "API-1", loads=loads(), engine_inputs=inputs, stop_after=3, clock=A.CLOCK, actor=A.ORC)

    def test_the_derived_loads_are_frozen_in_stage_1_and_checked_in_stage_3(self):
        b = building()
        b["tolerance_pct"] = 1
        res = self.run_api(b)
        self.assertTrue(res["ok"], res)
        stages = res["data"]["run"]["results"]
        self.assertIn("L-PB", [x["id"] for x in stages[0]["outputs"]["loads"]["loads"]])
        self.assertEqual(stages[2]["status"], "ok")
        self.assertTrue(stages[2]["outputs"]["lighting"]["load_check"][0]["within_tolerance"])

    def test_a_wrong_building_is_an_invalid_argument_that_lists_the_reasons(self):
        res = self.run_api(building(rooms={}, by_name={}))
        self.assertEqual((res["ok"], res["error"]["code"]), (False, "invalid_arguments"))
        self.assertTrue(res["error"]["details"]["errors"])

    def test_building_and_lighting_together_are_refused(self):
        res = self.run_api(building(), lighting={"document": {}})
        self.assertEqual((res["ok"], res["error"]["code"]), (False, "invalid_arguments"))
