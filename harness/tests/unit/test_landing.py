"""The landing page end to end without a browser: the request read by rules, the house proposed from it, the form checked, the project created and the run launched."""
from unittest import mock
import sys
import tempfile
import time
import unittest
from pathlib import Path

LANDING = Path(__file__).resolve().parents[2] / "tools" / "landing"
sys.path.insert(0, str(LANDING))
import brief  # noqa: E402
import build  # noqa: E402
import house  # noqa: E402
import pv  # noqa: E402
import runner  # noqa: E402
import server  # noqa: E402

REQUEST = "Creame una casa con 4 habitaciones, 2 baños, 1 jardín, y agrega iluminación y tomacorrientes"


class BriefTests(unittest.TestCase):
    def test_the_example_request_is_read_in_spanish(self):
        got = brief.interpret(REQUEST)
        self.assertEqual(got["rooms"], {"bedroom": 4, "bathroom": 2, "garden": 1})
        self.assertEqual(got["services"], {"lighting": True, "receptacles": True})
        self.assertEqual(got["disciplines"], ["architectural", "electrical"])

    def test_english_and_number_words(self):
        got = brief.interpret("Build a house with three bedrooms, two bathrooms, a kitchen and lighting")
        self.assertEqual((got["rooms"], got["services"]), ({"bedroom": 3, "bathroom": 2, "kitchen": 1}, {"lighting": True}))

    def test_what_is_not_there_is_not_invented(self):
        got = brief.interpret("")
        self.assertEqual((got["rooms"], got["services"], got["disciplines"]), ({}, {}, []))

    def test_what_the_harness_cannot_do_is_a_note_not_a_guess(self):
        got = brief.interpret("casa de dos plantas con aire acondicionado y 3 dormitorios")
        self.assertEqual((got["floors"], got["notes"]), (2, ["no_hvac_engine"]))
        self.assertIn("hvac", got["disciplines"])


class HouseTests(unittest.TestCase):
    def test_the_rooms_do_not_overlap_and_the_usual_ones_are_added_and_said(self):
        rows, added = house.propose({"bedroom": 4, "bathroom": 2})
        self.assertEqual(added, ["living", "kitchen"])
        self.assertEqual(len(rows), 8)
        for i, a in enumerate(rows):
            for b in rows[i + 1:]:
                x = min(a["east"], b["east"]) - max(a["west"], b["west"])
                y = min(a["north"], b["north"]) - max(a["south"], b["south"])
                self.assertFalse(x > 1e-9 and y > 1e-9, (a["code"], b["code"]))

    def test_the_reader_finds_the_rooms_that_were_drawn(self):
        for counts in ({"bedroom": 1}, {"bedroom": 2, "bathroom": 1, "garage": 1}, {"bedroom": 4, "bathroom": 2}, {"bedroom": 5, "bathroom": 3, "laundry": 1}):
            with self.subTest(counts=counts):
                rows, _ = house.propose(counts)
                _, plans, problem = build.check_floor({}, rows)
                self.assertIsNone(problem)
                self.assertIn("PB.dxf", plans)

    def test_two_floors_get_a_stair_on_both_and_the_reader_finds_every_room(self):
        rows, _ = house.propose({"bedroom": 4, "bathroom": 2}, "es", 2)
        self.assertEqual([p for p, _ in house.floors_of(rows)], ["PB", "P1"])
        self.assertEqual(sum(1 for r in rows if r["name"] == "Escalera"), 2)
        _, plans, problem = build.check_floor({}, rows)
        self.assertIsNone(problem)
        loads, inputs = build.engine_inputs({}, rows, list(plans))
        floors = inputs["building"]["floors"]
        self.assertEqual([f["id"] for f in floors], ["PB", "P1"])
        self.assertIn("shaft", floors[1])
        self.assertNotIn("shaft", floors[0])
        self.assertGreater(floors[1]["elevation_m"], 0)
        self.assertEqual([a["id"] for a in loads["areas"]], ["PB", "P1"])

    def test_rooms_with_missing_sizes_are_a_problem_not_a_crash(self):
        _, _, problem = build.check_floor({}, [{"code": "PB-01", "name": "X", "west": "0", "south": "", "east": "3", "north": "3"}])
        self.assertEqual(problem["code"], "rooms")
        self.assertEqual(build.check_floor({}, [])[2]["code"], "no_rooms")

    def test_the_inputs_of_the_building_follow_the_form(self):
        rows, _ = house.propose({"bedroom": 2, "bathroom": 1})
        loads, inputs = build.engine_inputs({"house.receptacles": "no", "house.garden_area_m2": 50}, rows, ["PB.dxf", "ISO.dxf"])
        b = inputs["building"]
        self.assertNotIn("receptacles", b)
        self.assertEqual(b["exterior"][0]["area_m2"], 50.0)
        self.assertEqual(b["presentation_sheets"], ["plans/ISO.dxf"])
        self.assertEqual(loads["loads"], [])
        self.assertEqual(set(b["floors"][0]["rooms"]), {r["code"] for r in rows})


def answers(it):
    vals = dict(it["values"])
    vals.update({"client.name": "Cliente Ficticio", "site.address": "Calle Ficticia 1", "supply.voltage.value": "400", "supply.earthing_system": "TT",
                 "supply.short_circuit_level.value": "6", "supply.short_circuit_level.origin": "dato ficticio"})
    return vals


class ServerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "projects"
        self.root.mkdir()
        self.folder = Path(tmp.name) / "projects" / "CASA-T1"

    def payload(self):
        it = server.interpret({"request": REQUEST, "lang": "es"})
        return {"discipline": it["brief"]["disciplines"], "request": REQUEST, "folder": str(self.folder), "docs": [], "answers": answers(it)}

    def test_interpret_fills_the_form_and_marks_the_proposals(self):
        it = server.interpret({"request": REQUEST, "lang": "en"})
        self.assertEqual(it["values"]["floor.name"], "GROUND FLOOR")
        self.assertEqual(len(it["values"]["floor.rooms"]), 8)
        self.assertEqual(it["values"]["house.garden_area_m2"], 108.0)
        self.assertIn("house.board_fp", it["assumed"])
        self.assertEqual(server.interpret({"request": "", "lang": "es"})["values"].get("floor.rooms"), None)

    def test_the_form_has_the_house_assumptions_when_both_disciplines_are_ticked(self):
        ids = [f["id"] for f in server.form_of("architectural,electrical")["forms"]]
        self.assertEqual(ids, ["architectural", "electrical", "house"])
        self.assertNotIn("house", [f["id"] for f in server.form_of("electrical")["forms"]])

    def test_check_writes_nothing_and_missing_earthing_is_reported(self):
        p = self.payload()
        ok = server.handle(self.root, p, False)
        self.assertEqual({k: v["state"] for k, v in ok["results"].items()}, {"electrical": "valid", "architectural": "valid"})
        self.assertFalse(self.folder.exists())
        del p["answers"]["supply.earthing_system"]
        bad = server.handle(self.root, p, False)
        self.assertEqual(bad["results"]["electrical"]["state"], "invalid")

    def test_submit_creates_the_project_with_its_plans_and_launches_the_run(self):
        calls = []

        def fake(root, args, timeout=120):
            calls.append(args)
            if args[2] == "init":
                return real(root, args, timeout)
            return {"ok": True, "data": {"mode": "edit", "run": {"summary": {"ok": True}, "results": []}}}
        real, server.run_epc = server.run_epc, fake
        self.addCleanup(setattr, server, "run_epc", real)
        r = server.handle(self.root, self.payload(), True)
        self.assertEqual(r["results"]["electrical"]["state"], "created")
        for _ in range(50):
            state = runner.status(r["job"])
            if state["state"] != "running":
                break
            time.sleep(0.1)
        self.assertEqual(state["state"], "done")
        self.assertTrue((self.folder / "inputs" / "plans" / "PB.dxf").is_file())
        self.assertTrue(any("run" in a for a in calls))

    def test_an_invalid_architecture_stops_before_anything_is_written(self):
        p = self.payload()
        p["answers"]["floor.rooms"] = [{"code": "PB-01", "name": "Sala", "west": "0", "south": "0", "east": "", "north": "3"}]
        r = server.handle(self.root, p, True)
        self.assertEqual(r["results"]["architectural"]["problem"]["code"], "rooms")
        self.assertFalse(self.folder.exists())


PV_ANSWERS = {"client.name": "Cliente Ficticio", "site.address": "Calle Ficticia 1", "site.installation_type": "Planta fotovoltaica", "supply.voltage.value": "400", "supply.earthing_system": "TT",
              "supply.short_circuit_level.value": "6", "supply.short_circuit_level.origin": "dato ficticio", "pv.mode": "ground", "pv.latitude_deg": "-34.6", "pv.longitude_deg": "-58.4",
              "pv.utc_offset_h": "-3", "pv.module": "longi.lr5-72hgd-560m", "pv.inverter": "sma.stp25000tl-30", "pv.isc_max_input_a": "49.5", "pv.target_kwp": "560", "pv.dc_ac_ratio": "1.2", "pv.aux_load_kw": "5", "pv.aux_phases": "3", "pv.aux_length_m": "60", "pv.board_fp": "0.9", "pv.site_width_m": "200", "pv.site_length_m": "120"}


class PvProjectTests(unittest.TestCase):
    """The photovoltaic project: latitude and longitude go to PVGIS before the project exists; the answer is stored as an input and named by the `pv` section."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "projects"
        self.root.mkdir()
        self.folder = self.root / "PV-T1"
        self.asked = []

        def fetch(flat):
            self.asked.append((flat["pv.latitude_deg"], flat["pv.longitude_deg"]))
            return '{"weather": {}, "source": {"status": "pending review"}}'
        real, pv.fetch_weather = pv.fetch_weather, fetch
        self.addCleanup(setattr, pv, "fetch_weather", real)

    def payload(self, **changes):
        answers = dict(PV_ANSWERS, **changes)
        return {"discipline": ["electrical", "pv"], "request": "planta fotovoltaica", "folder": str(self.folder), "docs": [], "answers": answers}

    def test_the_request_names_the_discipline_and_proposes_what_is_pending_review(self):
        it = server.interpret({"request": "Una planta fotovoltaica de 1 MWp", "lang": "es"})
        self.assertEqual(it["brief"]["disciplines"], ["electrical", "pv"])
        self.assertEqual(it["values"]["pv.dc_ac_ratio"], 1.2)
        self.assertNotIn("pv.utc_offset_h", it["values"])      # the time zone comes from the place, not from a proposal
        self.assertNotIn("pv.azimuth_deg", it["values"])
        self.assertNotIn("pv.tilt_deg", it["values"])
        self.assertIn("pv.dc_ac_ratio", it["assumed"])
        self.assertNotIn("pv.latitude_deg", it["values"])

    def test_the_form_comes_from_the_catalogs_and_asks_for_latitude_and_longitude(self):
        form = server.form_of("electrical,pv")["forms"]
        self.assertEqual([f["id"] for f in form], ["electrical", "pv"])
        fields = {f["path"]: f for f in form[1]["fields"]}
        self.assertTrue(fields["pv.latitude_deg"]["required"] and fields["pv.longitude_deg"]["required"])
        self.assertIn("longi.lr5-72hgd-560m", fields["pv.module"]["options"])
        self.assertIn("sma.stp25000tl-30", fields["pv.inverter"]["options"])

    def test_the_minimum_is_the_structure_and_the_place(self):
        minimal = {k: v for k, v in PV_ANSWERS.items() if not k.startswith("pv.")}
        minimal.update({"pv.mode": "ground", "pv.latitude_deg": "-34.6", "pv.longitude_deg": "-58.4", "pv.site_width_m": "60", "pv.site_length_m": "40"})
        r = server.handle(self.root, {**self.payload(), "answers": minimal}, False)
        self.assertEqual(r["results"]["pv"]["state"], "valid")
        section = pv.section(minimal)
        self.assertEqual(section["document"]["arrays"][0]["inverter"], "auto")
        self.assertTrue(section["layout"]["fill"])
        self.assertNotIn("target_modules", section["layout"])
        self.assertEqual(pv.aux_loads(minimal)[1][0]["power"]["value"], pv.DEFAULTS["aux"]["load_kw"])      # a project needs one load: typical proposal, pending review
        feeder = pv.feeders_of(minimal)
        self.assertEqual((feeder["phases"], feeder["length_m"]), (pv.DEFAULTS["feeder"]["phases"], pv.DEFAULTS["feeder"]["length_m"]))      # the feeder of each inverter: typical proposal, pending review
        roof = pv.section(dict(minimal, **{"pv.mode": "rooftop", "pv.roof_width_m": "12", "pv.roof_slope_m": "6"}))
        self.assertNotIn("target_modules", roof["flat_roof"])
        capped = pv.section(dict(minimal, **{"pv.target_kwp": "10"}))
        self.assertEqual(capped["layout"]["target_kwp"], 10.0)      # the module is still `auto`: the stage turns the cap into modules after the pick
        fixed = pv.section(dict(minimal, **{"pv.target_kwp": "10", "pv.module": "longi.lr5-72hgd-560m"}))
        self.assertGreater(fixed["layout"]["target_modules"], 0)
        self.assertTrue(section["document"]["arrays"][0]["module"]["auto"])
        self.assertNotIn("auto", fixed["document"]["arrays"][0]["module"])

    def test_a_mounting_structure_is_chosen_from_the_engine_list(self):
        minimal = {k: v for k, v in PV_ANSWERS.items() if not k.startswith("pv.")}
        minimal.update({"pv.mode": "ground", "pv.latitude_deg": "-34.6", "pv.longitude_deg": "-58.4", "pv.site_width_m": "60", "pv.site_length_m": "40"})
        self.assertNotIn("structure_id", pv.section(minimal)["layout"])      # automatic: no foundation is assumed
        ground = pv.structures()
        sid = next(k for k, family in ground.items() if family == "ground")
        self.assertEqual(pv.section(dict(minimal, **{"pv.structure_id": sid}))["layout"]["structure_id"], sid)
        self.assertIsNone(pv.check(dict(minimal, **{"pv.structure_id": sid})))
        self.assertEqual(pv.check(dict(minimal, **{"pv.structure_id": "no_such_structure"}))["code"], "pv_range")
        roof = next(k for k, family in ground.items() if family == "roof")
        self.assertEqual(pv.check(dict(minimal, **{"pv.structure_id": roof}))["code"], "pv_range")      # a roof structure on a ground plant
        self.assertIn(sid, {f["path"]: f for f in pv.form()["fields"]}["pv.structure_id"]["options"])

    def test_the_auxiliary_service_of_a_plant_only_run_carries_its_rcbo(self):
        minimal = {k: v for k, v in PV_ANSWERS.items() if not k.startswith("pv.")}
        minimal.update({"pv.mode": "ground", "pv.latitude_deg": "-34.6", "pv.longitude_deg": "-58.4", "pv.site_width_m": "60", "pv.site_length_m": "40"})
        data = server._merge_pv(None, {"section": {}, "files": {}, "aux": (pv.aux_loads(minimal), pv.board_of(minimal))})
        self.assertEqual(data["inputs"]["circuits"], {"AUX-01": {"kind": "rcbo"}})

    def test_the_time_zone_comes_from_the_place_unless_typed(self):
        v = lambda **k: pv.values_of({f"pv.{a}": b for a, b in k.items()})[0]      # noqa: E731
        self.assertEqual(pv.utc_offset(v(latitude_deg="-32.89", longitude_deg="-68.84")), -3.0)
        self.assertEqual(pv.utc_offset(v(latitude_deg="28.6", longitude_deg="77.2")), 5.5)
        self.assertEqual(pv.utc_offset(v(latitude_deg="40.4", longitude_deg="-3.7")), 1.0)      # standard time, not summer time
        self.assertEqual(pv.utc_offset(v(latitude_deg="-32.89", longitude_deg="-68.84", utc_offset_h="-4")), -4.0)

    def test_a_place_without_a_time_zone_is_asked_with_its_own_code(self):
        base = {k: v for k, v in PV_ANSWERS.items() if not k.startswith("pv.")}
        base.update({"pv.mode": "ground", "pv.latitude_deg": "0", "pv.longitude_deg": "-30", "pv.site_width_m": "60", "pv.site_length_m": "40"})      # open Atlantic
        with mock.patch.object(pv, "utc_offset", return_value=None):
            problem = pv.check(base)
        self.assertEqual(problem["code"], "pv_timezone")
        self.assertIn(problem["detail"], ("utc_offset_h", "timezonefinder"))

    def test_a_run_ended_by_a_signal_says_so(self):
        import subprocess
        done = subprocess.CompletedProcess([], -9, stdout="", stderr="")
        with mock.patch.object(server.subprocess, "run", return_value=done):
            res = server.run_epc(self.root, ["run", "X"])
        self.assertEqual(res["error"]["code"], "cli_killed")
        self.assertIn("memory", res["error"]["message"])
        self.assertIn("memoria", res["error"]["message"])

    def test_the_client_price_becomes_the_economics_key_and_none_is_invented(self):
        base = {k: v for k, v in PV_ANSWERS.items() if not k.startswith("pv.")}
        base.update({"pv.mode": "ground", "pv.latitude_deg": "-34.6", "pv.longitude_deg": "-58.4", "pv.site_width_m": "60", "pv.site_length_m": "40"})
        self.assertNotIn("economics", pv.section(base))
        priced = pv.section(dict(base, **{"pv.energy_price": "0.12", "pv.currency": "USD", "pv.investment": "9000"}))
        self.assertEqual(priced["economics"], {"energy_price": 0.12, "currency": "USD", "investment": 9000.0})
        self.assertEqual(pv.check(dict(base, **{"pv.energy_price": "-1"}))["code"], "pv_range")

    def test_the_simulation_folder_tmp_of_the_repository_is_accepted_and_the_rest_of_the_repository_is_not(self):
        repo = server.HARNESS.parent
        self.assertIsNone(server._checked_root({"folder": str(repo / "tmp" / "sim-01" / "PV-X")}, self.root)[2])
        self.assertEqual(server._checked_root({"folder": str(repo / "projects" / "PV-X")}, self.root)[2], "inside_repo")

    def test_the_advanced_fields_are_marked_and_the_data_sheet_gap_is_not_asked(self):
        fields = {f["path"]: f for f in pv.form()["fields"]}
        self.assertTrue(all(fields[k]["advanced"] for k in ("pv.module", "pv.inverter", "pv.dc_ac_ratio", "pv.target_kwp", "pv.aux_load_kw", "pv.utc_offset_h")))
        self.assertFalse(any(fields[k]["advanced"] or fields[k]["required"] is False for k in ("pv.latitude_deg", "pv.longitude_deg", "pv.mode")))
        self.assertIn("auto", fields["pv.inverter"]["options"])
        answers = dict(PV_ANSWERS)
        del answers["pv.isc_max_input_a"]
        self.assertIsNone(pv.check(answers))
        self.assertIsNone(pv.section(answers)["document"]["arrays"][0]["inverter"]["isc_max_input_a"])

    def test_check_asks_and_never_fills_what_the_catalog_lacks(self):
        self.assertEqual(server.handle(self.root, self.payload(), False)["results"]["pv"]["state"], "valid")
        self.assertEqual(self.asked, [])
        for name, code in (("pv.latitude_deg", "pv_missing"), ("pv.site_width_m", "pv_missing")):
            answers = dict(PV_ANSWERS)
            del answers[name]
            r = server.handle(self.root, {**self.payload(), "answers": answers}, False)
            self.assertEqual(r["results"]["pv"]["problem"]["code"], code, name)
        self.assertEqual(server.handle(self.root, self.payload(**{"pv.latitude_deg": "-95"}), False)["results"]["pv"]["problem"]["code"], "pv_range")
        self.assertEqual(server.handle(self.root, self.payload(**{"pv.latitude_deg": "sur"}), False)["results"]["pv"]["problem"]["code"], "pv_number")

    def test_pv_needs_the_electrical_discipline(self):
        r = server.handle(self.root, {**self.payload(), "discipline": ["pv"]}, False)
        self.assertEqual(r["results"]["pv"]["problem"]["code"], "pv_needs_electrical")

    def test_submit_asks_pvgis_stores_the_file_and_runs_with_the_section(self):
        calls = []

        def fake(root, args, timeout=120):
            calls.append(args)
            if args[2] == "init":
                return real(root, args, timeout)
            return {"ok": True, "data": {"mode": "edit", "run": {"summary": {"ok": True}, "results": []}}}
        real, server.run_epc = server.run_epc, fake
        self.addCleanup(setattr, server, "run_epc", real)
        r = server.handle(self.root, self.payload(), True)
        self.assertEqual(r["results"]["pv"]["state"], "created")
        self.assertEqual(self.asked, [("-34.6", "-58.4")])
        for _ in range(50):
            if runner.status(r["job"])["state"] != "running":
                break
            time.sleep(0.1)
        self.assertTrue((self.folder / "inputs" / "weather" / "weather_pvgis.json").is_file())
        import json
        inputs = json.loads(Path(next(a[a.index("--engine-inputs") + 1] for a in calls if "run" in a)).read_text(encoding="utf-8"))
        self.assertEqual(inputs["pv"]["weather_file"], "weather/weather_pvgis.json")
        self.assertNotIn("weather", inputs["pv"]["document"])
        self.assertEqual(inputs["pv"]["document"]["site"]["latitude_deg"], -34.6)
        array = inputs["pv"]["document"]["arrays"][0]
        self.assertEqual((array["inverter"]["isc_max_input_a"], array["n_modules"]), (49.5, 1000))
        self.assertNotIn("tilt_deg", array)
        self.assertNotIn("azimuth_deg", array)
        self.assertEqual(inputs["pv"]["layout"]["site"]["width_m"], 200.0)
        self.assertEqual(inputs["board"]["fp_default"], 0.9)

    def test_a_rooftop_plant_has_no_layout_and_a_pvgis_failure_creates_nothing(self):
        flat = pv.section(dict(PV_ANSWERS, **{"pv.mode": "rooftop", "pv.roof_width_m": "12", "pv.roof_slope_m": "6"}))
        self.assertEqual((sorted(k for k in flat if k in ("roof", "flat_roof", "layout")), flat["flat_roof"]["target_modules"], flat["flat_roof"]["width_m"]), (["flat_roof"], 1000, 12.0))
        roof = pv.section(dict(PV_ANSWERS, **{"pv.mode": "rooftop", "pv.roof_type": "pitched", "pv.roof_width_m": "12", "pv.roof_slope_m": "6"}))
        self.assertNotIn("layout", roof)
        self.assertEqual((roof["roof"]["target_modules"], roof["roof"]["planes"][0]["width_m"], "tilt_deg" in roof["roof"]["planes"][0]), (1000, 12.0, False))
        self.assertEqual(pv.check(dict(PV_ANSWERS, **{"pv.mode": "rooftop"}))["detail"], "roof_width_m, roof_slope_m")
        two = dict(PV_ANSWERS, **{"pv.mode": "rooftop", "pv.roof_type": "pitched", "pv.roof_width_m": "12", "pv.roof_slope_m": "6", "pv.tilt_deg": "25", "pv.azimuth_deg": "0",
                                  "pv.roof2_width_m": "8", "pv.roof2_slope_m": "5", "pv.roof2_azimuth_deg": "90"})
        self.assertIsNone(pv.check(two))
        planes = pv.section(two)["roof"]["planes"]
        self.assertEqual([(p["id"], p["width_m"], p.get("azimuth_deg"), "tilt_deg" in p) for p in planes], [("R1", 12.0, 0.0, True), ("R2", 8.0, 90.0, False)])
        self.assertIn("roof", pv.section(dict(two, **{"pv.roof_type": "flat"})))      # a second plane means the roof is not flat
        self.assertEqual(pv.check(dict(two, **{"pv.roof2_slope_m": ""}))["detail"], "roof2_width_m, roof2_slope_m")

        def down(flat):
            raise OSError("no route")
        pv.fetch_weather = down
        r = server.handle(self.root, self.payload(), True)
        self.assertEqual(r["results"]["pv"]["problem"]["code"], "pvgis")
        self.assertFalse(self.folder.exists())


class RunnerTests(unittest.TestCase):
    def test_progress_reads_only_the_lines_of_its_run_and_files_stay_inside_deliverables(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "P"
            (folder / ".epc").mkdir(parents=True)
            (folder / ".epc" / "epc-progress.txt").write_text(
                "header\n2026-11-19T00:00:00Z | run run-A | stage 1 intake | ok | -\n2026-11-19T00:00:01Z | run run-B | stage 1 intake | ok | -\n"
                "2026-11-19T00:00:02Z | run run-A | stage 2 requirements_inputs | blocked | a | b\n", encoding="utf-8")
            self.assertEqual([(x["stage"], x["status"]) for x in runner.progress(folder, "run-A")], [(1, "ok"), (2, "blocked")])
            (folder / "deliverables" / "TR-001" / "01_SLD").mkdir(parents=True)
            (folder / "deliverables" / "TR-001" / "01_SLD" / "a.dxf").write_text("x")
            (folder / "secret.txt").write_text("s")
            runner.JOBS["j"] = {"state": "done", "folder": folder, "run_id": "run-A", "error": None, "mode": None}
            self.assertIsNotNone(runner.file_of("j", "deliverables/TR-001/01_SLD/a.dxf"))
            self.assertIsNone(runner.file_of("j", "secret.txt"))
            self.assertIsNone(runner.file_of("j", "deliverables/../secret.txt"))
            self.assertEqual(runner.deliverables(folder)["folders"][0]["name"], "01_SLD")


if __name__ == "__main__":
    unittest.main()


class PvModel3dFormatFormTests(unittest.TestCase):
    def test_the_3d_format_choice_reaches_the_drawings_inputs_and_is_checked(self):
        self.assertEqual(pv.drawings_options({}), {})
        self.assertEqual(pv.drawings_options({"model3d_format": "freecad"}), {"model3d_format": "freecad"})
        base = {k: v for k, v in PV_ANSWERS.items() if not k.startswith("pv.")}
        base.update({"pv.mode": "ground", "pv.latitude_deg": "-34.6", "pv.longitude_deg": "-58.4", "pv.site_width_m": "60", "pv.site_length_m": "40", "pv.model3d_format": "step"})
        self.assertEqual(pv.check(base)["code"], "pv_range")
