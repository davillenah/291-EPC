"""Building intake: the recognised floors become lighting rooms and `L-<floor>` loads before stage 1 freezes the load list."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import epc_lighting as EL  # noqa: E402
import test_pipeline_wiring as W  # noqa: E402
from disciplines.electrical_lv.intake.building import BuildingError, derive, derive_all  # noqa: E402
from disciplines.electrical_lv.pipeline import STAGES, run  # noqa: E402

LUM = {"id": "LED1", "lamps": 1, "lamp_flux_lm": 3600, "power_w": 36}
DATA = {"activity": "task.reading", "luminaire": "LED1", "height_m": 2.8, "coefficient_of_utilisation": 0.6}
# two rectangular rooms and an L-shaped one, as epc_arch gives them (area and the box of the rectangles in metres)
ARCH = {"rooms": [{"id": "r1", "name": "OFICINA", "area_m2": 20.0, "size_m": [4.0, 5.0], "box_m": [0.0, 0.0, 4.0, 5.0]},
                  {"id": "r2", "name": "HALL", "area_m2": 12.0, "size_m": [3.0, 4.0], "box_m": [4.0, 0.0, 7.0, 4.0]},
                  {"id": "r3", "name": "L", "area_m2": 16.0, "size_m": [5.0, 5.0], "box_m": [0.0, 5.0, 5.0, 10.0]}]}


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


TUG = {"id": "tug", "name": "Socket outlet 2x10 A + E", "kind": "general", "poles": 2, "rated_a": 10, "power_va": 100, "height_m": 0.3, "ip": "IP20"}
PLUGS = {"use": "office", "receptacle": "tug"}


def with_plugs(**floor):
    b = building(**floor)
    b["receptacles"] = [dict(TUG)]
    f = b["floors"][0]
    f["receptacles_load"] = {"phases": 1, "length": {"value": 25, "unit": "m"}}
    for data in list(f["rooms"].values()) + list(f["by_name"].values()):
        data["receptacles"] = dict(PLUGS)
    return b


class ReceptacleTests(unittest.TestCase):
    def test_the_receptacle_load_is_the_load_of_the_engine_for_the_rooms(self):
        import epc_receptacles as ER
        out, section = derive(with_plugs(), loads())
        rooms = [dict(r, **PLUGS) for r in section["document"]["rooms"]]
        for r in rooms:
            for key in ("luminaire", "activity", "height_m", "coefficient_of_utilisation"):
                r.pop(key, None)
            r["receptacle"] = r.pop("receptacle", "tug")
            r.pop("use", None)
            r["use"] = "office"
        direct = ER.run({"schema_version": "1.0", "receptacles": [dict(TUG)], "rooms": rooms}).as_dict()
        load = [x for x in out["loads"] if x["id"] == "T-PB"][0]
        self.assertEqual((load["kind"], load["power"], load["phases"], load["length"]), ("receptacles", {"value": sum(r["load_va"] for r in direct["rooms"]), "unit": "VA"}, 1, {"value": 25, "unit": "m"}))

    def test_a_room_with_false_has_no_outlets_and_the_rest_are_required_to_say(self):
        b = with_plugs()
        b["floors"][0]["rooms"]["r3"]["receptacles"] = False
        out, _ = derive(b, loads())
        self.assertTrue([x for x in out["loads"] if x["id"] == "T-PB"])
        b = with_plugs()
        del b["floors"][0]["rooms"]["r3"]["receptacles"]
        with self.assertRaises(BuildingError) as ctx:
            derive(b, loads())
        self.assertIn("receptacles", ctx.exception.errors[0])

    def test_the_load_needs_its_phases_and_length_and_the_catalogue(self):
        b = with_plugs()
        del b["floors"][0]["receptacles_load"]
        with self.assertRaises(BuildingError) as ctx:
            derive(b, loads())
        self.assertIn("receptacles_load", ctx.exception.errors[0])
        b = with_plugs()
        del b["receptacles"]
        with self.assertRaises(BuildingError):
            derive(b, loads())

    def test_circuit_options_go_to_the_derived_loads(self):
        b = with_plugs()
        b["floors"][0]["circuits"] = {"lighting": {"kind": "mcb"}, "receptacles": {"kind": "rcbo"}}
        self.assertEqual(derive_all(b, loads())["circuits"], {"L-PB": {"kind": "mcb"}, "T-PB": {"kind": "rcbo"}})


class RoutingTests(unittest.TestCase):
    def routed(self, **floor):
        b = with_plugs(board={"x_m": 4.0, "y_m": 5.0}, **floor)
        return b, derive_all(b, loads())

    def test_each_branch_circuit_is_a_load_with_the_length_equivalent_to_the_moments(self):
        b, done = self.routed()
        design = done["routing"]["PB"]
        by_id = {x["id"]: x for x in done["loads"]["loads"]}
        self.assertNotIn("L-PB", by_id)                                     # a routed floor has no load by floor: its circuits are the loads
        self.assertNotIn("T-PB", by_id)
        self.assertEqual(sorted(c["load"] for c in design["circuits"].values()), sorted(i for i in by_id if i.startswith(("L-IUG", "T-TUG"))))
        for tag, c in design["circuits"].items():
            load = by_id[c["load"]]
            riser = b["floors"][0]["length"]["value"] if c["part"] == "lighting" else b["floors"][0]["receptacles_load"]["length"]["value"]
            self.assertGreater(c["moment_m"], 0)
            self.assertAlmostEqual(load["length"]["value"], riser + design["wiring"]["routes"][tag]["moment_length_m"], places=3)
            self.assertEqual((load["power"], load["kind"], load["area"]), ({"value": c["power"], "unit": c["unit"]}, c["part"], "PB"))
        self.assertEqual(done["circuits"][design["circuits"]["IUG-01"]["load"]], {"moments": True})

    def test_the_circuit_tags_are_unique_in_the_whole_building(self):
        b = with_plugs(board={"x_m": 4.0, "y_m": 5.0})
        second = copy.deepcopy(b["floors"][0])
        second["id"], second["name"] = "P1", "Floor 1"
        b["floors"].append(second)
        done = derive_all(b, loads())
        tags = [t for d in done["routing"].values() for t in d["circuits"]]
        self.assertEqual(len(tags), len(set(tags)))
        self.assertEqual(len([x for x in done["loads"]["loads"] if x["area"] in ("PB", "P1")]), len(tags))

    def test_the_design_has_runs_circuits_and_found_routes(self):
        _, done = self.routed()
        design = done["routing"]["PB"]
        self.assertTrue(design["runs"]["lines"])
        self.assertTrue(all(r["found"] for r in design["wiring"]["routes"].values()))
        self.assertEqual({c["family"] for c in design["wiring"]["circuits"]}, {"IUG", "TUG"})
        self.assertEqual(design["document"]["lines"][0]["id"], "RUN-001")

    def test_without_a_board_there_is_no_routing_and_the_length_is_the_given_one(self):
        done = derive_all(with_plugs(), loads())
        self.assertEqual(done["routing"], {})
        self.assertEqual([x for x in done["loads"]["loads"] if x["id"] == "L-PB"][0]["length"], {"value": 20, "unit": "m"})

    def test_a_room_without_position_in_metres_is_an_error(self):
        b = with_plugs(board={"x_m": 4.0, "y_m": 5.0})
        del b["floors"][0]["architecture"]["rooms"][0]["box_m"]
        with self.assertRaises(BuildingError) as ctx:
            derive_all(b, loads())
        self.assertIn("box_m", ctx.exception.errors[0])

    def test_a_wrong_board_is_named(self):
        with self.assertRaises(BuildingError) as ctx:
            derive_all(with_plugs(board={"x_m": 1}), loads())
        self.assertIn("board", ctx.exception.errors[0])


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


class RoutingStageTests(unittest.TestCase):
    """Stage 3 re-routes the derived design with `epc_plan.core.process` and checks it against the load list."""

    def stage(self, tamper=None):
        import epc_plan
        b = with_plugs(board={"x_m": 4.0, "y_m": 5.0})
        b["tolerance_pct"] = 1
        done = derive_all(b, loads())
        if tamper:
            tamper(done)
        inputs = dict(W.inputs_doc(), lighting=done["lighting"], routing=done["routing"])
        ctx = W.context(engine_inputs=inputs, loads=done["loads"])
        run(ctx, stop_after=2, run_id="r3")
        return done, STAGES[2].run(ctx), epc_plan

    def test_the_routes_are_the_engines_and_agree_with_the_loads(self):
        done, res, plan = self.stage()
        self.assertEqual(res.status, "ok", res.message)
        floor = res.outputs["routing"]["floors"]["PB"]
        self.assertEqual(set(floor["circuits"]), {c["tag"] for c in done["routing"]["PB"]["wiring"]["circuits"]})
        self.assertTrue(all(r["found"] for r in floor["circuits"].values()))
        self.assertIn({"engine": "cad/plan", "function": "epc_plan.core.process", "version": plan.__version__}, res.engine_calls)
        self.assertFalse([f for f in res.findings if f["severity"] == "major"])
        json.dumps(res.to_dict())

    def test_a_load_length_that_is_not_riser_plus_moments_is_a_finding(self):
        def tamper(done):
            [x for x in done["loads"]["loads"] if x["id"] == "L-IUG-01"][0]["length"]["value"] += 5
        _, res, _ = self.stage(tamper)
        self.assertEqual([f["field"] for f in res.findings if f["severity"] == "major"], ["L-IUG-01/length"])

    def test_a_circuit_load_with_another_power_is_a_finding(self):
        def tamper(done):
            [x for x in done["loads"]["loads"] if x["id"] == "T-TUG-01"][0]["power"]["value"] += 100
        _, res, _ = self.stage(tamper)
        self.assertEqual([f["field"] for f in res.findings if f["severity"] == "major"], ["T-TUG-01/power"])

    def test_a_recorded_route_that_changed_is_a_finding(self):
        def tamper(done):
            done["routing"]["PB"]["circuits"]["IUG-01"]["moment_m"] += 3
        _, res, _ = self.stage(tamper)
        self.assertIn("PB/IUG-01/moment_length_m", [f["field"] for f in res.findings])

    def test_a_wrong_section_blocks(self):
        inputs = dict(W.inputs_doc(), routing={"PB": {"nope": 1}})
        ctx = W.context(engine_inputs=inputs)
        run(ctx, stop_after=2, run_id="r3")
        res = STAGES[2].run(ctx)
        self.assertEqual(res.status, "blocked")
        self.assertTrue(res.message.startswith("routing: "))


class CableListTests(unittest.TestCase):
    """Stage 11: the cable list is selected from the engine result of stage 6 and joined with the containers of stage 3."""

    def documents(self, routed):
        b = with_plugs(**({"board": {"x_m": 4.0, "y_m": 5.0}} if routed else {}))
        done = derive_all(b, loads())
        inputs = dict(W.inputs_doc(), lighting=done["lighting"], **({"routing": done["routing"]} if routed else {}))
        inputs["circuits"] = dict(inputs["circuits"], **done["circuits"])
        ctx = W.context(engine_inputs=inputs, loads=done["loads"])
        res = run(ctx, stop_after=11, run_id="r", stages=[s for s in STAGES if s.number != 10])
        docs = res.results[-1]
        return ctx, docs, {d["name"]: d["document"] for d in docs.outputs["documents"]}.get("cable_list")

    def test_without_routing_the_list_stays_pending(self):
        _, docs, doc = self.documents(False)
        self.assertIsNone(doc)
        self.assertIn({"name": "cable list", "status": "planned"}, docs.outputs["pending_documents"])

    def test_one_row_per_sized_circuit_with_the_engine_values(self):
        ctx, docs, doc = self.documents(True)
        calc = ctx.engine_cache["chain"]["calc"]
        self.assertEqual([r["circuit"] for r in doc["rows"]], list(calc["datos"]))
        for row in doc["rows"]:
            self.assertEqual((row["s_mm2"], row["in_a"], row["du_pct"]), (calc["datos"][row["circuit"]]["S"], calc["datos"][row["circuit"]]["In"], calc["datos"][row["circuit"]]["dU"]))
        self.assertNotIn("cable list", [p["name"] for p in docs.outputs["pending_documents"]])

    def test_a_routed_circuit_has_its_own_row_with_its_room_and_containers(self):
        _, docs, doc = self.documents(True)
        rows = {r["circuit"]: r for r in doc["rows"]}
        self.assertTrue([k for k in rows if k.startswith("L-IUG")] and [k for k in rows if k.startswith("T-TUG")])
        self.assertNotIn("L-PB", rows)
        row = rows["L-IUG-01"]
        self.assertEqual((row["area"], row["raceway"]["circuit"]), ("PB", "IUG-01"))
        self.assertTrue(row["raceway"]["containers"] and row["raceway"]["room"])
        self.assertTrue(all(c["cables"] > 0 for c in row["raceway"]["containers"]))
        json.dumps(docs.to_dict())

    def test_the_cable_of_a_branch_is_sized_with_the_moments_flag(self):
        ctx, _, doc = self.documents(True)
        form = ctx.engine_cache["chain"]["form"]
        flagged = [c for c in form["circuits"] if c.get("moments")]
        self.assertEqual(sorted(c["tag"] for c in flagged), sorted(r["circuit"] for r in doc["rows"] if r["circuit"].startswith(("L-IUG", "T-TUG"))))


class SpecificationTests(unittest.TestCase):
    """The draft specification (provisional structure, PLG-01): built from the results of the run, with every missing datum as a gap."""

    def documents(self, routed=True):
        helper = CableListTests()
        ctx, docs, _ = helper.documents(routed)
        return ctx, docs, {d["name"]: d["document"] for d in docs.outputs["documents"]}

    def test_it_has_the_provisional_sections_and_leaves_the_pending_list(self):
        _, docs, by_name = self.documents()
        spec = by_name["specification"]
        self.assertEqual([s["id"] for s in spec["sections"]], [str(i) for i in range(1, 12)])
        self.assertEqual((spec["status"], spec["document"]), ("draft", "specification"))
        self.assertIn("provisional", spec["structure"])
        self.assertNotIn("specification", [p["name"] for p in docs.outputs["pending_documents"]])

    def test_every_figure_is_read_from_the_run(self):
        ctx, _, by_name = self.documents()
        spec = by_name["specification"]
        tech = [s for s in spec["sections"] if s["id"] == "6"][0]
        tables = [b for b in tech["blocks"] if b["type"] == "table"]
        rows = by_name["cable_list"]["rows"]
        self.assertEqual([r[0] for r in tables[0]["rows"]], [r["circuit"] for r in rows])
        self.assertEqual([r[3] for r in tables[1]["rows"]], [r["s_mm2"] for r in rows])
        limits = ctx.results[6].outputs["voltage_drop"]["limits_pct"]
        accept = [s for s in spec["sections"] if s["id"] == "8"][0]
        self.assertEqual([b for b in accept["blocks"] if b["type"] == "table"][0]["rows"], [list(x) for x in sorted(limits.items())])

    def test_what_the_project_does_not_have_is_a_gap_with_who_must_give_it(self):
        _, _, by_name = self.documents()
        gaps = by_name["specification"]["gaps"]
        self.assertTrue(gaps and all(g["text"].startswith("[DEFINIR]") and g["who"] for g in gaps))
        self.assertEqual(sorted({g["section"] for g in gaps}), ["10", "11", "3", "5", "6", "7"])

    def test_without_routing_it_stays_pending(self):
        _, docs, by_name = self.documents(False)
        self.assertNotIn("specification", by_name)
        self.assertIn({"name": "specification", "status": "planned"}, docs.outputs["pending_documents"])


class FloorPlanTests(unittest.TestCase):
    """Stage 10: a plan and a lighting plan per routed floor, as DXF, through `epc_plan.dxfout`."""

    def drawings(self):
        import tempfile
        import ezdxf
        b = with_plugs(board={"x_m": 4.0, "y_m": 5.0})
        arch = b["floors"][0]["architecture"]
        arch["units_per_metre"] = 100.0
        arch["walls"] = [{"id": "w1", "a": [0, 0], "b": [700, 0], "thickness": 20.0}, {"id": "w2", "a": [700, 0], "b": [700, 1000], "thickness": 20.0}]
        done = derive_all(b, loads())
        inputs = dict(W.inputs_doc(), lighting=done["lighting"], routing=done["routing"])
        with tempfile.TemporaryDirectory() as tmp:
            ctx = W.context(engine_inputs=inputs, loads=done["loads"], work_dir=tmp)
            res = run(ctx, stop_after=10, run_id="r10")
            out = Path(tmp) / res.results[9].outputs["directory"]
            files = sorted(f["path"] for f in res.results[9].outputs["files"])
            docs = {p.name: ezdxf.readfile(str(p)) for p in out.glob("*.dxf")}
        return res.results[9], files, docs

    def test_each_routed_floor_has_a_plan_and_a_lighting_plan(self):
        res, files, docs = self.drawings()
        self.assertEqual(res.status, "ok", res.message)
        plans = [f for f in files if "_plan_" in f or "_lighting_" in f]
        self.assertEqual([p.split("_", 1)[1] for p in plans], ["lighting_PB.dxf", "plan_PB.dxf"])
        self.assertIn({"engine": "cad/plan", "function": "epc_plan.dxfout.write_dxf", "version": __import__("epc_plan").__version__}, res.engine_calls)

    def test_the_lighting_plan_has_only_luminaires_and_the_plan_has_the_outlets_and_the_walls(self):
        _, _, docs = self.drawings()
        plan = next(d for n, d in docs.items() if "_plan_PB" in n)
        light = next(d for n, d in docs.items() if "_lighting_PB" in n)
        blocks = lambda d: {e.dxf.name for e in d.modelspace().query("INSERT")}   # noqa: E731
        self.assertIn("SYM_TOMACORRIENTE", blocks(plan))
        self.assertNotIn("SYM_TOMACORRIENTE", blocks(light))
        self.assertIn("SYM_LUMINARIA", blocks(light))
        self.assertTrue([e for e in plan.modelspace().query("LWPOLYLINE") if e.dxf.layer.endswith("ARQ-MUROS")])

    def test_without_routing_no_floor_plan_is_written(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            ctx = W.context(work_dir=tmp)
            res = run(ctx, stop_after=10, run_id="r10")
            self.assertFalse([f for f in res.results[9].outputs["files"] if "_plan_" in f["path"]])


class WholeBuildingTests(unittest.TestCase):
    """The 12 stages from the building section alone: derived loads, routing, plans, cable list and the transmittal."""

    def test_the_whole_pipeline_runs_from_the_building_and_issues_the_plans(self):
        import tempfile
        import test_platform_api as A
        from epc_platform import api
        b = with_plugs(board={"x_m": 4.0, "y_m": 5.0})
        b["tolerance_pct"] = 1
        b["floors"][0]["architecture"]["units_per_metre"] = 100.0
        b["floors"][0]["architecture"]["walls"] = [{"id": "w1", "a": [0, 0], "b": [700, 0], "thickness": 20.0}]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api.init_project(root, "API-1", A.ANSWERS, clock=A.CLOCK, actor=A.ORC)
            res = api.run_pipeline(root / "API-1", loads=loads(), engine_inputs=dict(W.inputs_doc(), building=b, transformer={"demand_kva": 40, "reserve_pct": 20, "secondary_v": 400}), clock=A.CLOCK, actor=A.ORC)
            self.assertTrue(res["ok"], res)
            run_ = res["data"]["run"]
            self.assertEqual(run_["summary"]["by_status"], {"ok": 12})
            self.assertEqual(res["data"]["workflow_state"], "draft_ready")
            names = sorted(p.name for p in (root / "API-1" / "deliverables" / "TR-001").glob("*.dxf"))
            self.assertTrue([n for n in names if "_plan_PB" in n] and [n for n in names if "_lighting_PB" in n])
            docs = [d["name"] for d in run_["results"][10]["outputs"]["documents"]]
            self.assertIn("cable_list", docs)
