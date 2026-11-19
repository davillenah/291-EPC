"""The landing page end to end without a browser: the request read by rules, the house proposed from it, the form checked, the project created and the run launched."""
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
