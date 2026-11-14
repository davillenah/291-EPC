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
from disciplines.electrical_lv.store import ProjectStore  # noqa: E402

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


class StudiesTests(unittest.TestCase):
    """The studies of stage 11 are selections of the memo, the load schedule and the routing: no figure of their own."""

    def docs(self):
        helper = CableListTests()
        ctx, _, _ = helper.documents(True)
        res = ctx.results[11]
        return ctx, {d["name"]: d["document"] for d in res.outputs["documents"]}

    def test_the_short_circuit_study_has_one_row_per_protection_with_the_engine_values(self):
        ctx, docs = self.docs()
        memo = ctx.engine_cache["chain"]["memo"]
        detail = [s for s in docs["short_circuit_study"]["sections"] if s["title"] == "Detail"][0]["blocks"][0]["rows"]
        self.assertEqual([r[0] for r in detail], [c["tag"] for c in memo["circuits"]])
        self.assertEqual([r[4] for r in detail], [c["proteccion"]["icu_ka"] for c in memo["circuits"]])

    def test_the_selectivity_study_counts_what_the_memo_counts(self):
        ctx, docs = self.docs()
        counts = ctx.engine_cache["chain"]["memo"]["resumen"]["selectividad"]
        summary = docs["selectivity_study"]["sections"][0]["blocks"][0]["rows"][0]
        self.assertEqual(summary, [counts["total"], counts["parcial"], counts["revisar"]])

    def test_the_load_schedule_is_the_one_of_stage_3(self):
        ctx, docs = self.docs()
        rows = docs["load_schedule"]["sections"][0]["blocks"][0]["rows"]
        self.assertEqual([r[0] for r in rows], [c["circuit"] for c in ctx.results[3].outputs["load_schedule"]["circuits"]])

    def test_the_raceway_memo_has_a_section_per_routed_floor(self):
        _, docs = self.docs()
        self.assertEqual([s["title"] for s in docs["raceway_memo"]["sections"]], ["Floor PB"])
        self.assertTrue(docs["raceway_memo"]["sections"][0]["blocks"][3]["rows"])

    def test_without_routing_there_are_no_studies(self):
        _, docs, _ = CableListTests().documents(False)
        names = {d["name"] for d in docs.outputs["documents"]}
        self.assertFalse(names & {"short_circuit_study", "selectivity_study", "load_schedule", "raceway_memo"})


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
            files = sorted(f["path"] for f in res.results[9].outputs.get("files", []))
            docs = {p.name: ezdxf.readfile(str(p)) for p in out.glob("*.dxf")}
        return res.results[9], files, docs

    def test_each_routed_floor_has_a_plan_and_a_lighting_plan(self):
        res, files, docs = self.drawings()
        self.assertEqual(res.status, "ok", res.message)
        plans = [f for f in files if ("_plan_" in f or "_lighting_" in f) and not f.endswith("_sheet.dxf")]
        self.assertEqual([p.split("_", 1)[1] for p in plans], ["lighting_PB.dxf", "plan_PB.dxf"])
        self.assertIn({"engine": "cad/plan", "function": "epc_plan.dxfout.write_dxf", "version": __import__("epc_plan").__version__}, res.engine_calls)

    def test_the_lighting_plan_has_only_luminaires_and_the_plan_has_the_outlets_and_the_walls(self):
        _, _, docs = self.drawings()
        plan = next(d for n, d in docs.items() if n.endswith("_plan_PB.dxf"))
        light = next(d for n, d in docs.items() if n.endswith("_lighting_PB.dxf"))
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


class ExtraSlicesTests(unittest.TestCase):
    """Slices that call engine functions the pipeline did not call: they run on building runs or with their own section, and invent nothing."""

    def stage6(self, **inputs):
        b = with_plugs(board={"x_m": 4.0, "y_m": 5.0})
        done = derive_all(b, loads())
        ins = dict(W.inputs_doc(), lighting=done["lighting"], routing=done["routing"], **inputs)
        ins["circuits"] = dict(ins["circuits"], **done["circuits"])
        ctx = W.context(engine_inputs=ins, loads=done["loads"])
        res = run(ctx, stop_after=6, run_id="r6")
        return ctx, res.results[2], (res.results[5] if len(res.results) > 5 else None)

    def test_a_building_run_has_motors_reactive_and_panel_thermal(self):
        _, _, s6 = self.stage6()
        self.assertEqual(s6.status, "ok", s6.message)
        for section in ("motors", "reactive", "panel_thermal"):
            self.assertIn(section, s6.outputs)
        self.assertEqual([m["circuit"] for m in s6.outputs["motors"]["motors"]], ["M-01"])
        self.assertIn({"engine": "calculation/aea90364", "function": "epc_aea90364.aea_motor.caida_arranque", "version": __import__("epc_aea90364").__version__}, s6.engine_calls)
        self.assertTrue([f for f in s6.findings if f["field"] == "assumption"])

    def test_the_motor_figures_are_the_engines(self):
        from epc_aea90364 import aea_motor
        ctx, _, s6 = self.stage6()
        row = s6.outputs["motors"]["motors"][0]
        detail = ctx.engine_cache["chain"]["calc"]["detalle"]["M-01"]
        direct = aea_motor.proteccion_motor(detail["ib_a"], row["topology"])
        self.assertEqual(row["protection"], direct)

    def test_reactive_says_where_the_target_comes_from(self):
        _, _, s6 = self.stage6()
        self.assertIn("engine default", s6.outputs["reactive"]["target_origin"])
        _, _, s6 = self.stage6(reactive={"target_fp": 0.95})
        self.assertEqual((s6.outputs["reactive"]["target_fp"], s6.outputs["reactive"]["target_origin"]), (0.95, "engine_inputs"))

    def test_panel_thermal_is_verified_only_against_a_given_admissible_power(self):
        _, _, s6 = self.stage6()
        self.assertNotIn("complies", s6.outputs["panel_thermal"])
        _, _, s6 = self.stage6(panel_thermal={"p_admissible_w": 1.0})
        self.assertFalse(s6.outputs["panel_thermal"]["complies"])
        self.assertTrue([f for f in s6.findings if f["severity"] == "major"])

    def test_backup_lightning_and_hvac_need_their_sections(self):
        _, s3, s6 = self.stage6()
        self.assertNotIn("backup", s6.outputs)
        self.assertNotIn("lightning", s6.outputs)
        self.assertNotIn("hvac", s3.outputs)

    def test_backup_runs_for_the_named_loads_and_blocks_on_an_unknown_one(self):
        _, _, s6 = self.stage6(backup={"genset": {"loads": ["M-01"]}, "ups": {"loads": ["E-01"], "autonomy_min": 15}})
        self.assertEqual(s6.status, "ok", s6.message)
        self.assertEqual(set(s6.outputs["backup"]), {"genset", "transfer_switch_a", "ups"})
        _, _, s6 = self.stage6(backup={"genset": {"loads": ["X-99"]}})
        self.assertEqual(s6.status, "blocked")
        self.assertIn("X-99", s6.message)

    def test_lightning_has_no_default(self):
        _, _, s6 = self.stage6(lightning={"length_m": 20})
        self.assertEqual(s6.status, "blocked")
        self.assertIn("missing", s6.message)

    def test_without_a_building_the_golden_style_run_is_unchanged(self):
        ctx = W.context()
        res = run(ctx, stop_after=6, run_id="r6")
        for section in ("motors", "reactive", "panel_thermal", "backup", "lightning"):
            self.assertNotIn(section, res.results[5].outputs)

    def test_hvac_runs_in_stage_3_for_its_document_and_blocks_on_a_bad_one(self):
        import epc_hvac
        doc = {"design": {"t_out_c": 35, "t_in_c": 24, "w_out_kg_kg": 0.018, "w_in_kg_kg": 0.0093, "supply_delta_t_k": 10},       # synthetic test conditions
               "spaces": [{"id": "S1", "name": "Office", "area_m2": 50, "height_m": 3, "use": "office", "occupants": 10, "lighting_w_m2": 10, "equipment_w_m2": 15}]}
        _, s3, _ = self.stage6(hvac=doc)
        self.assertEqual(s3.status, "ok", s3.message)
        self.assertEqual(s3.outputs["hvac"]["hvac"], epc_hvac.run(copy.deepcopy(doc)).as_dict())
        _, s3, _ = self.stage6(hvac={"design": {}, "spaces": []})
        self.assertEqual(s3.status, "blocked")


class PhaseBalanceSliceTests(unittest.TestCase):
    def test_a_building_run_assigns_the_phases_with_the_engine(self):
        from epc_load_balance import phase_balance as PB
        b = with_plugs(board={"x_m": 4.0, "y_m": 5.0})
        done = derive_all(b, loads())
        ins = dict(W.inputs_doc(), lighting=done["lighting"], routing=done["routing"])
        ins["circuits"] = dict(ins["circuits"], **done["circuits"])
        ctx = W.context(engine_inputs=ins, loads=done["loads"])
        res = run(ctx, stop_after=3, run_id="r3")
        out = res.results[2].outputs["phase_balance"]
        self.assertEqual(res.results[2].status, "ok")
        self.assertEqual(len(out["totals"]), 3)
        self.assertAlmostEqual(sum(out["totals"]), sum(sum(v) for v in out["circuits"].values()), places=9)
        self.assertEqual(out["limit_pct"], PB.aea_demand.DESEQUILIBRIO_MAX_PCT)
        self.assertIn("epc_load_balance.phase_balance.balance", [c["function"] for c in res.results[2].engine_calls])

    def test_without_a_building_or_the_list_the_slice_does_not_run(self):
        ctx = W.context()
        res = run(ctx, stop_after=3, run_id="r3")
        self.assertNotIn("phase_balance", res.results[2].outputs)


class RacewaySizingAndCoordinationTests(unittest.TestCase):
    def stage6(self, **inputs):
        return ExtraSlicesTests().stage6(**inputs)

    def test_each_run_gets_the_smallest_size_that_holds_its_cables(self):
        import epc_plan.sizing as sizing
        ctx, _, s6 = self.stage6()
        self.assertEqual(s6.status, "ok", s6.message)
        sized = s6.outputs["raceway_sizing"]["floors"]["PB"]
        self.assertTrue(sized and all(s["fits"] and s["used_pct"] <= s["limit_pct"] for s in sized))
        self.assertIn({"engine": "cad/plan", "function": "epc_plan.sizing.size_containers", "version": __import__("epc_plan").__version__}, s6.engine_calls)
        self.assertTrue(all(isinstance(s["size"], dict) for s in sized))
        self.assertTrue(hasattr(sizing, "size_containers"))

    def test_coordination_needs_its_section_and_reports_the_clashes_of_the_engine(self):
        _, _, s6 = self.stage6()
        self.assertNotIn("coordination", s6.outputs)
        _, _, s6 = self.stage6(coordination={"documents": []})
        self.assertEqual(s6.status, "ok", s6.message)
        self.assertEqual(set(s6.outputs["coordination"]), {"elements", "clashes"})
        self.assertGreater(s6.outputs["coordination"]["elements"], 0)


class EmergencyAndExteriorTests(unittest.TestCase):
    def build(self):
        b = building()
        b["floors"][0]["emergency"] = {"r1": {"luminaire": "LED1", "height_m": 2.8}}
        b["exterior"] = [{"id": "EXT1", "name": "Yard", "area_m2": 300, "luminaire": "LED1", "activity": "circulation.indoor",
                          "load": {"area": "A1", "phases": 1, "length": {"value": 40, "unit": "m"}}}]
        return b

    def test_the_emergency_and_the_exterior_go_to_the_lighting_document(self):
        done = derive_all(self.build(), loads())
        doc = done["lighting"]["document"]
        self.assertEqual([e["id"] for e in doc["emergency"]], ["PB-r1-EM"])
        self.assertAlmostEqual(doc["emergency"][0]["width_m"] * doc["emergency"][0]["length_m"], 20.0, places=2)
        self.assertEqual([a["id"] for a in doc["areas"]], ["EXT1"])
        self.assertNotIn("load", doc["areas"][0])

    def test_the_exterior_makes_a_load_with_the_engine_power(self):
        import epc_lighting
        done = derive_all(self.build(), loads())
        direct = epc_lighting.run(copy.deepcopy(done["lighting"]["document"])).as_dict()
        load = [x for x in done["loads"]["loads"] if x["id"] == "L-EXT1"][0]
        self.assertEqual(load["power"], {"value": direct["areas"][0]["energy"]["installed_power_w"], "unit": "W"})
        self.assertEqual((load["area"], load["phases"], load["length"]), ("A1", 1, {"value": 40, "unit": "m"}))

    def test_stage_3_checks_the_emergency_and_the_exterior_with_the_engine(self):
        done = derive_all(self.build(), loads())
        ins = dict(W.inputs_doc(), lighting=done["lighting"])
        ctx = W.context(engine_inputs=ins, loads=done["loads"])
        run(ctx, stop_after=2, run_id="r")
        res = STAGES[2].run(ctx)
        self.assertEqual(res.status, "ok", res.message)
        self.assertEqual((res.outputs["lighting"]["counts"]["areas"], res.outputs["lighting"]["counts"]["emergency"]), (1, 1))

    def test_a_wrong_emergency_room_or_an_exterior_without_its_load_is_an_error(self):
        b = self.build()
        b["floors"][0]["emergency"] = {"r9": {}}
        with self.assertRaises(BuildingError):
            derive_all(b, loads())
        b = self.build()
        del b["exterior"][0]["load"]
        with self.assertRaises(BuildingError) as ctx:
            derive_all(b, loads())
        self.assertIn("exterior", ctx.exception.errors[0])


class RenderedDocumentsTests(unittest.TestCase):
    def run_api(self, **extra):
        import tempfile
        import test_platform_api as A
        from epc_platform import api
        b = with_plugs(board={"x_m": 4.0, "y_m": 5.0})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api.init_project(root, "API-1", A.ANSWERS, clock=A.CLOCK, actor=A.ORC)
            ins = dict(W.inputs_doc(), building=b, transformer={"demand_kva": 40, "reserve_pct": 20, "secondary_v": 400}, **extra)
            res = api.run_pipeline(root / "API-1", loads=loads(), engine_inputs=ins, clock=A.CLOCK, actor=A.ORC)
            files = sorted(p.name for p in (root / "API-1" / "deliverables" / "TR-001").glob("*"))
        return res, files

    def test_a_building_run_issues_pdf_word_and_workbook_files_of_the_documents(self):
        res, files = self.run_api()
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["data"]["run"]["summary"]["by_status"], {"ok": 12})
        for name in ("calculation_memo.pdf", "calculation_memo.docx", "cable_list.pdf", "specification.docx", "short_circuit_study.pdf"):
            self.assertIn(name, files)
        self.assertTrue([f for f in files if f.endswith("_tables.xlsx")])
        rendered = res["data"]["run"]["results"][10]["outputs"]["rendered"]
        self.assertIn("terminal_block_list", rendered["not_rendered"])

    def test_the_formats_can_be_chosen_and_a_wrong_one_blocks(self):
        res, files = self.run_api(documents={"formats": ["pdf"]})
        self.assertTrue(res["ok"], res)
        self.assertFalse([f for f in files if f.endswith((".docx", ".xlsx"))])
        res, _ = self.run_api(documents={"formats": ["odt"]})
        self.assertEqual(res["data"]["run"]["results"][10]["status"], "blocked")


class MultilineTests(unittest.TestCase):
    def files(self, **extra):
        import tempfile
        b = with_plugs(board={"x_m": 4.0, "y_m": 5.0})
        done = derive_all(b, loads())
        ins = dict(W.inputs_doc(), lighting=done["lighting"], routing=done["routing"], **extra)
        ins["circuits"] = dict(ins["circuits"], **done["circuits"])
        with tempfile.TemporaryDirectory() as tmp:
            ctx = W.context(engine_inputs=ins, loads=done["loads"], work_dir=tmp)
            res = run(ctx, stop_after=10, run_id="r10")
            return res.results[9], sorted(f["path"] for f in res.results[9].outputs.get("files", []))

    def test_a_building_run_draws_the_multiline_diagram_too(self):
        res, files = self.files()
        self.assertEqual(res.status, "ok", res.message)
        self.assertEqual(res.outputs["summary"]["diagrams"], ["sld", "mld"])
        self.assertTrue([f for f in files if f.startswith("MLD_")], files)

    def test_the_diagrams_can_be_chosen_and_a_wrong_one_blocks(self):
        res, files = self.files(drawings={"diagrams": ["sld"]})
        self.assertFalse([f for f in files if f.startswith("MLD_")])
        res, _ = self.files(drawings={"diagrams": ["xyz"]})
        self.assertEqual(res.status, "blocked")


class PlanSheetTests(unittest.TestCase):
    def test_each_plan_goes_on_the_iram_sheet_with_the_project_title_block(self):
        res, files = MultilineTests().files()
        self.assertEqual(res.status, "ok", res.message)
        sheets = [f for f in files if f.endswith("_sheet.dxf")]
        self.assertEqual(len(sheets), 2, files)
        self.assertEqual(sorted(res.outputs["plan_sheets"]), sorted(s[:-len("_sheet.dxf")] for s in sheets))
        self.assertTrue(all(v["format"] == "A1" and v["scale"] > 0 for v in res.outputs["plan_sheets"].values()))
        self.assertIn("epc_drawing.export.plan_sheet.compose", [c["function"] for c in res.engine_calls])

    def test_the_format_and_scale_come_from_the_drawings_input_and_a_wrong_one_blocks(self):
        res, _ = MultilineTests().files(drawings={"sheet_format": "A3", "paper_scale": 200})
        self.assertEqual(res.status, "ok", res.message)
        self.assertTrue(all(v["format"] == "A3" for v in res.outputs["plan_sheets"].values()))
        res, _ = MultilineTests().files(drawings={"sheet_format": "B7"})
        self.assertEqual(res.status, "blocked")


class ResumeTests(unittest.TestCase):
    """RUN-01: `resume` finds the first stage that reads a changed input and reuses the stages before it."""

    def test_the_first_stage_of_each_kind_of_change(self):
        from disciplines.electrical_lv import resume as RS
        base = RS.signatures({"a": 1}, {"l": 1}, {"transformer": {"x": 1}, "boq": {"y": 1}, "other": 1})
        same = RS.signatures({"a": 1}, {"l": 1}, {"transformer": {"x": 1}, "boq": {"y": 1}, "other": 1})
        self.assertEqual(RS.first_stage(base, same), 12)
        for change, stage in (({"transformer": {"x": 2}, "boq": {"y": 1}, "other": 1}, 4), ({"transformer": {"x": 1}, "boq": {"y": 2}, "other": 1}, 11),
                              ({"transformer": {"x": 1}, "boq": {"y": 1}, "other": 2}, 3), ({"transformer": {"x": 1}, "boq": {"y": 1}, "other": 1, "drawings": {"date": "d"}}, 10),
                              ({"transformer": {"x": 2}, "boq": {"y": 2}, "other": 1}, 4)):
            with self.subTest(change=change):
                self.assertEqual(RS.first_stage(base, RS.signatures({"a": 1}, {"l": 1}, change)), stage)
        for answers, loads in (({"a": 2}, {"l": 1}), ({"a": 1}, {"l": 2})):
            with self.assertRaises(RS.NothingToResume):
                RS.first_stage(base, RS.signatures(answers, loads, {}))

    def test_a_resumed_run_reuses_the_earlier_stages_and_a_changed_load_list_is_refused(self):
        import tempfile
        import test_platform_api as A
        from epc_platform import api
        b = with_plugs(board={"x_m": 4.0, "y_m": 5.0})
        trafo = {"demand_kva": 40, "reserve_pct": 20, "secondary_v": 400}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api.init_project(root, "API-1", A.ANSWERS, clock=A.CLOCK, actor=A.ORC)
            store = ProjectStore(root / "API-1")

            def corrected():
                with store.pipeline_session("seed") as token:
                    store.write_workflow(token, {"state": "corrected", "history": []})

            first = api.run_pipeline(root / "API-1", loads=loads(), engine_inputs=dict(W.inputs_doc(), building=b, transformer=trafo), clock=A.CLOCK, actor=A.ORC, run_id="r1")
            self.assertTrue(first["ok"], first)
            corrected()
            same = api.run_pipeline(root / "API-1", loads=loads(), engine_inputs=dict(W.inputs_doc(), building=b, transformer=trafo), clock=A.CLOCK, actor=A.ORC, run_id="r2", resume=True)
            self.assertTrue(same["ok"], same)
            self.assertEqual(same["data"]["run"]["summary"]["reused"], list(range(1, 12)))
            corrected()
            changed = api.run_pipeline(root / "API-1", loads=loads(), engine_inputs=dict(W.inputs_doc(), building=b, transformer=dict(trafo, reserve_pct=30)), clock=A.CLOCK, actor=A.ORC,
                                       run_id="r3", resume=True)
            self.assertTrue(changed["ok"], changed)
            self.assertEqual(changed["data"]["run"]["summary"]["reused"], [1, 2, 3])
            corrected()
            more = loads()
            more["loads"].append(dict(more["loads"][0], id="X-99"))
            refused = api.run_pipeline(root / "API-1", loads=more, engine_inputs=dict(W.inputs_doc(), building=b, transformer=trafo), clock=A.CLOCK, actor=A.ORC, run_id="r4", resume=True)
            self.assertEqual((refused["ok"], refused["error"]["code"]), (False, "cannot_resume"))
            both = api.run_pipeline(root / "API-1", loads=loads(), engine_inputs=dict(W.inputs_doc(), building=b), clock=A.CLOCK, actor=A.ORC, resume=True, from_stage=3)
            self.assertEqual(both["error"]["code"], "invalid_arguments")


class PlanFromInputsTests(unittest.TestCase):
    """A floor can name its plan (a DXF of `inputs/`): the pipeline recognises it with epc_arch instead of taking the recognised architecture as data."""

    def building(self, plan="plans/PB.dxf"):
        data = {"activity": "task.reading", "luminaire": "LED1", "height_m": 2.8, "coefficient_of_utilisation": 0.6}
        return {"luminaires": [dict(LUM)], "floors": [{"id": "PB", "name": "Ground floor", "phases": 1, "length": {"value": 20, "unit": "m"}, "plan": plan, "rooms": {"r1": data}}]}

    def project(self, tmp, name="PB.dxf", data=None):
        sys.path.insert(0, str(Path(W.__file__).resolve().parents[2] / "src" / "engines" / "cad" / "arch" / "tests"))
        import helpers
        plans = Path(tmp) / "inputs" / "plans"
        plans.mkdir(parents=True, exist_ok=True)
        (plans / name).write_bytes(data if data is not None else helpers.room_dxf())
        return Path(tmp) / "inputs"

    def test_the_architecture_is_what_epc_arch_recognises_in_the_file(self):
        import tempfile
        import epc_arch
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self.project(tmp)
            done = derive_all(self.building(), loads(), inputs)
            direct = epc_arch.recognize((inputs / "plans" / "PB.dxf").read_bytes(), "PB.dxf").architecture.as_dict()
        rooms = done["lighting"]["document"]["rooms"]
        self.assertEqual([r["id"] for r in rooms], ["PB-r1"])
        self.assertAlmostEqual(rooms[0]["width_m"] * rooms[0]["length_m"], direct["rooms"][0]["area_m2"], places=2)

    def test_a_missing_file_a_path_outside_inputs_and_both_keys_are_errors(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self.project(tmp)
            for plan in ("plans/none.dxf", "../outside.dxf"):
                with self.subTest(plan=plan), self.assertRaises(BuildingError) as ctx:
                    derive_all(self.building(plan), loads(), inputs)
                self.assertIn("not a file of the inputs folder", ctx.exception.errors[0])
            both = self.building()
            both["floors"][0]["architecture"] = {"rooms": []}
            with self.assertRaises(BuildingError):
                derive_all(both, loads(), inputs)

    def test_a_file_the_engine_cannot_read_is_an_error(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self.project(tmp, data=b"not a dxf at all")
            with self.assertRaises(BuildingError) as ctx:
                derive_all(self.building(), loads(), inputs)
        self.assertIn("cannot be read", ctx.exception.errors[0])

    def test_through_the_api_the_plan_of_the_inputs_folder_feeds_the_run(self):
        import tempfile
        import test_platform_api as A
        from epc_platform import api
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api.init_project(root, "API-1", A.ANSWERS, clock=A.CLOCK, actor=A.ORC)
            self.project(root / "API-1")
            res = api.run_pipeline(root / "API-1", loads=loads(), engine_inputs=dict(W.inputs_doc(), building=self.building()), stop_after=3, clock=A.CLOCK, actor=A.ORC)
        self.assertTrue(res["ok"], res)
        self.assertIn("L-PB", [x["id"] for x in res["data"]["run"]["results"][0]["outputs"]["loads"]["loads"]])


class VerticalRiserTests(unittest.TestCase):
    """The run from the main board to the board of each floor, routed by the plan engine with the height of the shaft."""

    def build(self):
        b = with_plugs(board={"x_m": 4.0, "y_m": 5.0})
        for key in ("length",):
            del b["floors"][0][key]
        del b["floors"][0]["receptacles_load"]["length"]
        b["floors"][0]["elevation_m"] = 0.0
        second = copy.deepcopy(b["floors"][0])
        second.update({"id": "P1", "name": "Floor 1", "elevation_m": 3.2, "shaft": {"x_m": 1.0, "y_m": 8.0}})
        b["floors"].append(second)
        b["main_board"] = {"floor": "PB", "x_m": 1.0, "y_m": 8.0}
        return b

    def test_the_riser_is_the_horizontal_runs_plus_the_height_of_the_shaft(self):
        done = derive_all(self.build(), loads())
        pb, p1 = done["routing"]["PB"], done["routing"]["P1"]
        self.assertEqual(pb["riser_route"]["height_m"], 0.0)
        self.assertAlmostEqual(pb["riser_route"]["length_m"], abs(4.0 - 1.0) + abs(5.0 - 8.0), places=3)          # main (1, 8) to the board (4, 5)
        self.assertEqual(p1["riser_route"]["height_m"], 3.2)
        self.assertAlmostEqual(p1["riser_route"]["length_m"], 3.2 + abs(4.0 - 1.0) + abs(5.0 - 8.0), places=3)    # the shaft at (1, 8): up 3.2 m, then to the board
        self.assertEqual(p1["riser_m"], {"lighting": p1["riser_route"]["length_m"], "receptacles": p1["riser_route"]["length_m"]})

    def test_the_loads_of_the_upper_floor_use_the_routed_riser(self):
        done = derive_all(self.build(), loads())
        design = done["routing"]["P1"]
        by_id = {x["id"]: x for x in done["loads"]["loads"]}
        for tag, c in design["circuits"].items():
            self.assertAlmostEqual(by_id[c["load"]]["length"]["value"], design["riser_route"]["length_m"] + c["moment_m"], places=2)

    def test_a_typed_length_a_missing_level_or_shaft_and_a_wrong_main_floor_are_errors(self):
        b = self.build()
        b["floors"][1]["length"] = {"value": 5, "unit": "m"}
        with self.assertRaises(BuildingError) as ctx:
            derive_all(b, loads())
        self.assertIn("routed from the main board", ctx.exception.errors[0])
        for key in ("elevation_m", "shaft"):
            b = self.build()
            del b["floors"][1][key]
            with self.subTest(key=key), self.assertRaises(BuildingError) as ctx:
                derive_all(b, loads())
            self.assertIn(key, ctx.exception.errors[0])
        b = self.build()
        b["main_board"]["floor"] = "XX"
        with self.assertRaises(BuildingError):
            derive_all(b, loads())

    def test_the_stage_checks_the_loads_against_the_riser_of_the_design(self):
        done = derive_all(self.build(), loads())
        ins = dict(W.inputs_doc(), lighting=done["lighting"], routing=done["routing"])
        ins["circuits"] = dict(ins["circuits"], **done["circuits"])
        ctx = W.context(engine_inputs=ins, loads=done["loads"])
        run(ctx, stop_after=2, run_id="r")
        res = STAGES[2].run(ctx)
        self.assertEqual(res.status, "ok", res.message)
        self.assertFalse([f for f in res.findings if f["severity"] == "major"])

    def test_a_shaft_away_from_both_boards_adds_both_horizontal_legs_and_the_height(self):
        b = self.build()
        b["floors"][1]["shaft"] = {"x_m": 6.0, "y_m": 8.0}
        p1 = derive_all(b, loads())["routing"]["P1"]["riser_route"]
        # main (1, 8) -> shaft (6, 8): 5 m; up 3.2 m; shaft (6, 8) -> board (4, 5): 3 + 2 = 5 m
        self.assertAlmostEqual(p1["length_m"], 5.0 + 3.2 + 5.0, places=3)

    def test_a_shaft_at_the_floor_board_is_the_board(self):
        b = self.build()
        b["floors"][1]["shaft"] = {"x_m": 4.0, "y_m": 5.0}
        p1 = derive_all(b, loads())["routing"]["P1"]["riser_route"]
        self.assertAlmostEqual(p1["length_m"], 3.0 + 3.0 + 3.2, places=3)


class TransmittalCoverTests(unittest.TestCase):
    def test_a_building_run_issues_the_cover_pdf_of_the_transmittal_and_a_run_without_pdf_does_not(self):
        res, files = RenderedDocumentsTests().run_api()
        self.assertTrue(res["ok"], res)
        self.assertIn("TR-001_transmittal.pdf", files)
        out = res["data"]["run"]["results"][11]["outputs"]
        self.assertNotIn("TR-001_transmittal", [f["name"] for f in out["transmittal"]["files"]])       # it lists the files: it is not one of them
        res, files = RenderedDocumentsTests().run_api(documents={"formats": ["docx"]})
        self.assertTrue(res["ok"], res)
        self.assertNotIn("TR-001_transmittal.pdf", files)

    def test_the_data_lists_every_file_with_its_short_hash_and_the_unverified_records(self):
        from disciplines.electrical_lv.stages import rendering
        rows = [{"name": "a", "code": "C-1", "path": "a.dxf", "sha256": "0123456789abcdef" * 4}, {"name": "memo", "code": None, "path": None, "sha256": "f" * 64}]
        data = rendering.transmittal_data("TR-007", "P-1", "R1", "run-1", rows, [{"review_status": "verified"}, {"review_status": "pending"}])
        self.assertEqual((data["subtitle"], [r[4] for r in data["rows"]], data["rows"][1][3]), ("TR-007", ["0123456789ab", "ffffffffffff"], "(structured document)"))
        self.assertIn("1 of 2 norm records", data["sections"][0][1])


class SpecialLocationsTests(unittest.TestCase):
    def build(self, **data):
        b = building()
        b["floors"][0]["special"] = {"r1": dict({"type": "bathroom", "conductor_current_a": 16, "distance_m": 0.5, "partition_width_m": 0.2}, **data)}
        return b

    def stage6(self, b):
        done = derive_all(b, loads())
        ins = dict(W.inputs_doc(), lighting=done["lighting"], special_locations={"locations": done["special"]})
        ctx = W.context(engine_inputs=ins, loads=done["loads"])
        res = run(ctx, stop_after=6, run_id="r6")
        return done, res.results[-1]

    def test_the_building_declares_the_kind_of_room_and_the_engine_is_called(self):
        from epc_aea90364 import aea_special_locations as SL
        done, s6 = self.stage6(self.build())
        self.assertEqual(done["special"][0]["room"], "PB-r1")
        self.assertEqual(s6.status, "ok", s6.message)
        row = s6.outputs["special_locations"]["locations"][0]
        self.assertEqual((row["induction_t"], row["induction_complies"], row["zone2_radius_m"]), (SL.induccion_conductor_t(16, 0.5), SL.induccion_admisible(16, 0.5), SL.radio_zona2_con_tabique_m(0.2)))

    def test_an_electric_vehicle_room_uses_the_multiple_load_rule_and_a_failure_is_a_finding(self):
        from epc_aea90364 import aea_special_locations as SL
        b = building()
        b["floors"][0]["special"] = {"r2": {"type": "ev_charging", "outlets": 12, "points": 12, "circuit_current_a": 32, "max_point_current_a": 16, "max_demand": 30, "installed_load": 60}}
        _, s6 = self.stage6(b)
        row = s6.outputs["special_locations"]["locations"][0]
        self.assertEqual(row["multiple_load"], SL.load_multiple_complies(12, 12, 32, 16))
        self.assertEqual(row["demand_factor"], 0.5)
        self.assertFalse(row["multiple_load"]["cumple"])
        self.assertEqual([f["field"] for f in s6.findings if f["severity"] == "major"], ["PB-r2/special_location_complies"])

    def test_a_missing_datum_blocks_and_a_wrong_room_or_kind_is_an_error(self):
        b = self.build()
        del b["floors"][0]["special"]["r1"]["distance_m"]
        _, s6 = self.stage6(b)
        self.assertEqual(s6.status, "blocked")
        self.assertIn("distance_m", s6.message)
        for special in ({"r9": {"type": "bathroom"}}, {"r1": {"type": "sauna"}}):
            bad = building()
            bad["floors"][0]["special"] = special
            with self.assertRaises(BuildingError):
                derive_all(bad, loads())

    def test_without_the_section_nothing_runs_and_the_api_refuses_two_sources(self):
        ctx = W.context()
        res = run(ctx, stop_after=6, run_id="r6")
        self.assertNotIn("special_locations", res.results[5].outputs)
        import tempfile
        import test_platform_api as A
        from epc_platform import api
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            api.init_project(root, "API-1", A.ANSWERS, clock=A.CLOCK, actor=A.ORC)
            out = api.run_pipeline(root / "API-1", loads=loads(), engine_inputs=dict(W.inputs_doc(), building=self.build(), special_locations={"locations": []}), stop_after=3, clock=A.CLOCK, actor=A.ORC)
        self.assertEqual(out["error"]["code"], "invalid_arguments")
