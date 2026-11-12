"""MIG-31: the project SSOT files, their schemas and the write rule (only a running pipeline writes the SSOT).

Synthetic data in temp folders only; nothing is written inside the repository's projects/ tree.
"""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from disciplines.electrical_lv import store as S
from disciplines.electrical_lv.intake.profile import TEMPLATE, build_profile
from disciplines.electrical_lv.intake.schema_check import load_schema, validate
from disciplines.electrical_lv.pipeline import STAGES, PipelineContext, run
from disciplines.electrical_lv.recorder import progress_line
from disciplines.electrical_lv.store import PipelineToken, ProjectStore, StoreError

TEMPLATE_DIR = TEMPLATE.parent
CLOCK = lambda: "2026-01-01T00:00:00Z"  # noqa: E731
ANSWERS = {
    "project_code": "TEST-001",
    "client": {"name": "Synthetic Client"},
    "site": {"address": "Nowhere 1", "installation_type": "test"},
    "supply": {"earthing_system": "TN", "short_circuit_level": {"value": 10, "unit": "kA", "origin": "declared by test"}},
    "language": "en",
}
LOADS = {
    "schema_version": "1.0",
    "areas": [{"id": "A1", "name": "One", "plan": "plans/a1.dxf"}],
    "loads": [{"id": "L1", "description": "lamp", "area": "A1", "kind": "lighting", "power": {"value": 1, "unit": "kW"}, "phases": 3}],
}
PROFILE_SCHEMA = "project_profile.schema.json"
STATE_SCHEMA = "master_project_state.schema.json"


def tree_bytes(root):
    """{relative path: bytes} of every file under root (empty folders do not count)."""
    root = Path(root)
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


class TempCase(unittest.TestCase):
    def tmp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        return Path(holder.name)

    def new_store(self, name="proj", plan=True):
        store = ProjectStore(self.tmp() / name)
        store.init_from_template()
        if plan:
            store.write_input("plans/a1.dxf", "plan")
        return store

    def loads_path(self):
        path = self.tmp() / "loads.json"
        path.write_text(json.dumps(LOADS), encoding="utf-8")
        return str(path)

    def context(self, store):
        return PipelineContext(answers=ANSWERS, load_list_path=self.loads_path(), store=store)

    def run_to(self, store, stop_after, run_id="r1", **kwargs):
        return run(self.context(store), stop_after=stop_after, run_id=run_id, clock=CLOCK, **kwargs)


class SchemaTests(unittest.TestCase):
    def check(self, data, schema):
        return validate(data, load_schema(schema))

    def test_the_profile_intake_produces_validates(self):
        self.assertEqual(self.check(build_profile(ANSWERS), PROFILE_SCHEMA), [])
        full = dict(ANSWERS, criteria={"set": "default", "exceptions": ["x"]}, engineer_of_record={"name": "N", "registration": "R", "college": "C"},
                    supply=dict(ANSWERS["supply"], source="grid", voltage={"value": 400, "unit": "V"}))
        self.assertEqual(self.check(build_profile(full), PROFILE_SCHEMA), [])

    def test_the_template_validates_as_template(self):
        profile = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        state = json.loads((TEMPLATE_DIR / S.STATE).read_text(encoding="utf-8"))
        self.assertEqual(profile["status"], "template")
        self.assertEqual(self.check(profile, PROFILE_SCHEMA), [])
        self.assertEqual(self.check(state, STATE_SCHEMA), [])

    def test_nulls_are_allowed_only_while_the_status_is_template(self):
        profile = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        profile["status"] = "draft"
        errors = self.check(profile, PROFILE_SCHEMA)
        for field in ("project_code", "client.name", "site.address", "site.installation_type", "supply.earthing_system", "supply.short_circuit_level"):
            self.assertTrue(any(e.startswith(field) for e in errors), (field, errors))
        state = json.loads((TEMPLATE_DIR / S.STATE).read_text(encoding="utf-8"))
        state["status"] = "running"
        self.assertEqual(self.check(state, STATE_SCHEMA), ["pipeline_run_id: must be of type string"])

    def test_profile_rejects_unknown_fields_and_bad_values(self):
        profile = build_profile(ANSWERS)
        self.assertTrue(self.check(dict(profile, extra=1), PROFILE_SCHEMA))
        self.assertTrue(self.check(dict(profile, status="approved"), PROFILE_SCHEMA))
        self.assertTrue(self.check(dict(profile, language="fr"), PROFILE_SCHEMA))
        self.assertTrue(self.check({k: v for k, v in profile.items() if k != "supply"}, PROFILE_SCHEMA))

    def test_state_rejects_bad_stage_and_finding_shapes(self):
        state = json.loads((TEMPLATE_DIR / S.STATE).read_text(encoding="utf-8"))
        state.update(status="running", pipeline_run_id="r1")
        good = dict(number=1, slug="intake", status="ok", started=None, finished=None, finding_count=0)
        self.assertEqual(self.check(dict(state, stages=[good]), STATE_SCHEMA), [])
        self.assertTrue(self.check(dict(state, stages=[dict(good, status="weird")]), STATE_SCHEMA))
        self.assertTrue(self.check(dict(state, stages=[dict(good, finding_count=-1)]), STATE_SCHEMA))
        self.assertTrue(self.check(dict(state, open_findings=[{"id": "F-1"}]), STATE_SCHEMA))

    def test_the_conditional_keyword_of_the_validator(self):
        schema = {"type": "object", "if": {"required": ["a"], "properties": {"a": {"enum": [1]}}},
                  "then": {"required": ["b"]}, "else": {"required": ["c"]}}
        self.assertEqual(validate({"a": 1, "b": 0}, schema), [])
        self.assertEqual(validate({"a": 1}, schema), ["b: is required"])
        self.assertEqual(validate({"a": 2, "c": 0}, schema), [])
        self.assertEqual(validate({"a": 2}, schema), ["c: is required"])
        self.assertEqual(validate({"b": 0}, {"if": {"required": ["a"]}, "then": {"required": ["z"]}}), [])


class InitTests(TempCase):
    def test_init_copies_the_template_structure_without_readmes(self):
        store = self.new_store(plan=False)
        for name in S.SUBDIRS:
            self.assertTrue((store.root / name).is_dir(), name)
        files = sorted(tree_bytes(store.root))
        self.assertEqual(files, ["epc-progress.txt", "master_project_state.json", "project_profile.json"])
        self.assertEqual(store.read_profile()["status"], "template")
        self.assertFalse(store.is_frozen())

    def test_init_refuses_a_folder_that_already_holds_something(self):
        store = self.new_store()
        with self.assertRaises(StoreError):
            store.init_from_template()
        other = self.tmp() / "x"
        other.mkdir()
        (other / "f.txt").write_text("x", encoding="utf-8")
        with self.assertRaises(StoreError):
            ProjectStore(other).init_from_template()

    def test_init_refuses_to_write_inside_the_repository_template(self):
        with self.assertRaises(StoreError):
            ProjectStore(TEMPLATE_DIR / "new_project").init_from_template()
        with self.assertRaises(StoreError):
            ProjectStore(TEMPLATE_DIR).init_from_template()
        self.assertFalse((TEMPLATE_DIR / "new_project").exists())


class WriteRuleTests(TempCase):
    def test_a_token_cannot_be_built_by_hand(self):
        with self.assertRaises(PermissionError):
            PipelineToken("r1", Path("."))
        with self.assertRaises(PermissionError):
            PipelineToken("r1", Path("."), _mint=object())

    def test_every_ssot_write_needs_a_token(self):
        store = self.new_store()
        profile = build_profile(ANSWERS)
        writes = [lambda t: store.write_profile(t, profile), lambda t: store.write_state(t, store.read_state()),
                  lambda t: store.append_progress(t, "line"), lambda t: store.write_ssot(t, "a.json", {}),
                  lambda t: store.freeze_inputs(t), lambda t: store.make_run_dir(t, "r1")]
        for i, write in enumerate(writes):
            for bad in (None, "token", object()):
                with self.subTest(write=i, token=bad), self.assertRaises(PermissionError):
                    write(bad)
        self.assertEqual(store.read_profile()["status"], "template")
        self.assertFalse(store.is_frozen())
        self.assertFalse((store.root / "ssot" / "a.json").exists())

    def test_a_token_of_another_project_or_a_closed_session_is_refused(self):
        a, b = self.new_store("a"), self.new_store("b")
        with a.pipeline_session("r1") as token:
            a.write_ssot(token, "ok.json", {"x": 1})
            with self.assertRaises(PermissionError):
                b.write_ssot(token, "ok.json", {"x": 1})
        with self.assertRaises(PermissionError):
            a.write_ssot(token, "late.json", {})
        self.assertEqual(a.read_ssot("ok.json"), {"x": 1})
        self.assertFalse((b.root / "ssot" / "ok.json").exists())

    def test_session_run_id_must_be_a_safe_name(self):
        store = self.new_store()
        for bad in ("", "../x", "a/b", "a b", None, "-x"):
            with self.subTest(run_id=bad), self.assertRaises(StoreError):
                with store.pipeline_session(bad):
                    pass

    def test_profile_and_state_are_checked_against_their_schemas(self):
        store = self.new_store()
        with store.pipeline_session("r1") as token:
            with self.assertRaises(StoreError):
                store.write_profile(token, {"status": "draft"})
            with self.assertRaises(StoreError):
                store.write_state(token, {"status": "running"})
            store.write_profile(token, build_profile(ANSWERS))
        self.assertEqual(store.read_profile()["project_code"], "TEST-001")

    def test_paths_that_escape_the_project_are_refused(self):
        store = self.new_store()
        outside = store.root.parent / "outside.json"
        with store.pipeline_session("r1") as token:
            for bad in ("../outside.json", "a/../../outside.json", "/abs.json", "C:/abs.json", "C:rel.json", "a\\b.json", "a//b.json",
                        "./a.json", "a/./b.json", "../.json", "", None):
                with self.subTest(name=bad), self.assertRaises(StoreError):
                    store.write_ssot(token, bad, {})
            with self.assertRaises(StoreError):
                store.write_ssot(token, "notjson.txt", {})
            with self.assertRaises(StoreError):
                store.make_run_dir(token, "../x")
            store.write_ssot(token, "sub/deep.json", {"ok": True})
        self.assertFalse(outside.exists())
        self.assertEqual(store.read_ssot("sub/deep.json"), {"ok": True})
        for bad in ("../x", "/x", "a/../../x", "a\\b"):
            with self.subTest(input=bad), self.assertRaises(StoreError):
                store.write_input(bad, "x")

    def test_a_symlink_that_leaves_the_project_is_refused(self):
        store = self.new_store()
        target = self.tmp()
        link = store.root / "ssot" / "link"
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:  # Windows without the symlink privilege: a junction is the same thing for path resolution
            subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True)
        with store.pipeline_session("r1") as token, self.assertRaises(StoreError):
            store.write_ssot(token, "link/escape.json", {})
        self.assertFalse((target / "escape.json").exists())

    def test_the_inputs_manifest_is_written_only_by_freeze(self):
        store = self.new_store()
        with store.pipeline_session("r1") as token:
            with self.assertRaises(StoreError):
                store.write_ssot(token, S.MANIFEST_NAME, {"files": []})
            store.freeze_inputs(token)
            with self.assertRaises(StoreError):
                store.freeze_inputs(token)

    def test_progress_entries_are_single_lines(self):
        store = self.new_store()
        with store.pipeline_session("r1") as token:
            store.append_progress(token, "one")
            for bad in ("a\nb", "a\rb", 5):
                with self.assertRaises(StoreError):
                    store.append_progress(token, bad)
        self.assertTrue(store.read_progress().endswith("one\n"))


class InputsTests(TempCase):
    def frozen(self):
        store = self.new_store()
        store.write_input("loads/l.csv", b"a,b\n1,2\n")
        with store.pipeline_session("r1") as token:
            manifest = store.freeze_inputs(token)
        return store, manifest

    def test_freeze_writes_the_manifest_and_marks_the_inputs_frozen(self):
        store, manifest = self.frozen()
        self.assertTrue(store.is_frozen())
        self.assertEqual(store.read_ssot(S.MANIFEST_NAME), manifest)
        self.assertEqual([f["path"] for f in manifest["files"]], ["loads/l.csv", "plans/a1.dxf"])
        self.assertEqual(store.verify_inputs_unchanged("r1"), [])

    def test_verify_detects_changed_added_and_removed_files(self):
        store, _ = self.frozen()
        (store.inputs_dir / "plans" / "a1.dxf").write_text("edited", encoding="utf-8")
        (store.inputs_dir / "plans" / "new.dxf").write_text("new", encoding="utf-8")
        (store.inputs_dir / "loads" / "l.csv").unlink()
        findings = store.verify_inputs_unchanged("r9")
        self.assertEqual(sorted((f["field"], f["value"]) for f in findings),
                         [("inputs/loads/l.csv", "missing"), ("inputs/plans/a1.dxf", "changed"), ("inputs/plans/new.dxf", "added")])
        for f in findings:
            self.assertEqual((f["severity"], f["run_id"], f["status"]), ("blocking", "r9", "open"))
        self.assertEqual(validate(findings, {"type": "array", "items": load_schema(STATE_SCHEMA)["properties"]["open_findings"]["items"]}), [])

    def test_inputs_cannot_be_written_after_the_freeze(self):
        store, _ = self.frozen()
        with self.assertRaises(StoreError):
            store.write_input("plans/late.dxf", "x")
        self.assertFalse((store.inputs_dir / "plans" / "late.dxf").exists())

    def test_verify_before_the_freeze_is_an_error(self):
        with self.assertRaises(StoreError):
            self.new_store().verify_inputs_unchanged()


class FileFormatTests(TempCase):
    def test_json_is_deterministic_lf_utf8(self):
        text = S.dumps({"b": 1, "a": {"z": "ñ", "y": [1, 2]}})
        self.assertEqual(text, '{\n  "a": {\n    "y": [\n      1,\n      2\n    ],\n    "z": "ñ"\n  },\n  "b": 1\n}\n')
        self.assertNotIn("\r", text)
        with self.assertRaises(StoreError):
            S.dumps({"x": {1, 2}})
        with self.assertRaises(StoreError):
            S.dumps({"x": float("nan")})

    def test_atomic_write_leaves_no_temp_file_and_keeps_the_old_content_on_failure(self):
        store = self.new_store()
        with store.pipeline_session("r1") as token:
            store.write_ssot(token, "a.json", {"v": 1})
            with self.assertRaises(StoreError):
                store.write_ssot(token, "a.json", {"v": {1}})
            store.write_state(token, dict(store.read_state()))
            store.write_ssot(token, "a.json", {"v": 2})
        self.assertEqual(store.read_ssot("a.json"), {"v": 2})
        self.assertEqual([p for p in store.root.rglob("*") if p.name.endswith(".tmp")], [])

    def test_a_failed_replace_removes_its_temp_file(self):
        folder = self.tmp()
        target = folder / "sub"          # a folder: os.replace onto it fails
        target.mkdir()
        with self.assertRaises(OSError):
            S.atomic_write(target, b"x")
        self.assertEqual([p.name for p in folder.iterdir()], ["sub"])

    def test_the_progress_line_format(self):
        stage = STAGES[0]
        res = stage.result("blocked", message="a | b\nc")
        self.assertEqual(progress_line("T", "r1", stage, res), "T | run r1 | stage 1 intake | blocked | a / b c")
        self.assertEqual(progress_line(None, "r1", stage, stage.result("ok")), "- | run r1 | stage 1 intake | ok | -")


class PipelineWithStoreTests(TempCase):
    def test_a_run_writes_the_profile_state_progress_and_stage_files(self):
        store = self.new_store()
        res = self.run_to(store, 4)
        self.assertEqual([r.status for r in res.results], ["ok", "ok", "ok", "blocked"])
        self.assertEqual(store.read_profile(), build_profile(ANSWERS))
        self.assertTrue(store.is_frozen())
        names = sorted(p.name for p in (store.root / "ssot").iterdir())
        self.assertEqual(names, ["inputs_manifest.json", "stage_01_intake.json", "stage_02_requirements.json",
                                 "stage_03_input_verification.json", "stage_04_load_schedule.json"])
        for r in res.results:
            spec = STAGES[r.stage - 1].spec
            on_disk = store.read_ssot(f"stage_{r.stage:02d}_{spec.slug}.json")
            self.assertEqual(on_disk, json.loads(json.dumps(r.to_dict())))
        progress = store.read_progress().splitlines()
        self.assertEqual(progress[2:], [
            "2026-01-01T00:00:00Z | run r1 | stage 1 intake | ok | -",
            "2026-01-01T00:00:00Z | run r1 | stage 2 requirements | ok | -",
            "2026-01-01T00:00:00Z | run r1 | stage 3 input_verification | ok | -",
            f"2026-01-01T00:00:00Z | run r1 | stage 4 load_schedule | blocked | {res.results[3].message.replace('|', '/')}"])
        self.assertEqual(store.read_ssot("stage_01_intake.json")["outputs"]["inputs_manifest"], store.read_ssot(S.MANIFEST_NAME))

    def test_the_state_follows_the_run(self):
        store = self.new_store()
        res = self.run_to(store, 4)
        state = store.read_state()
        self.assertEqual(validate(state, load_schema(STATE_SCHEMA)), [])
        self.assertEqual((state["status"], state["pipeline_run_id"]), ("blocked", "r1"))
        self.assertEqual([(s["number"], s["slug"], s["status"], s["finding_count"]) for s in state["stages"]],
                         [(1, "intake", "ok", 0), (2, "requirements", "ok", 0), (3, "input_verification", "ok", 0),
                          (4, "load_schedule", "blocked", len(res.results[3].findings))])
        self.assertEqual({(s["started"], s["finished"]) for s in state["stages"]}, {("2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z")})
        self.assertEqual(state["open_findings"], res.results[3].findings)
        self.assertTrue(state["open_findings"])

    def test_a_partial_run_is_paused_and_a_full_walk_is_completed(self):
        store = self.new_store()
        self.run_to(store, 3)
        self.assertEqual(store.read_state()["status"], "paused")
        self.assertEqual(store.read_state()["open_findings"], [])
        self.assertTrue((store.root / "runs" / "r1").is_dir())

    def test_a_rerun_keeps_revisions_and_signatures(self):
        store = self.new_store()
        self.run_to(store, 3)
        with store.pipeline_session("manual") as token:
            state = dict(store.read_state(), signatures=[{"by": "engineer"}], revisions=[{"rev": "A"}])
            store.write_state(token, state)
        self.run_to(store, 3, run_id="r2")
        state = store.read_state()
        self.assertEqual((state["pipeline_run_id"], state["signatures"], state["revisions"]), ("r2", [{"by": "engineer"}], [{"rev": "A"}]))

    def test_a_changed_input_blocks_stage_2(self):
        store = self.new_store()
        self.run_to(store, 3)
        (store.inputs_dir / "plans" / "a1.dxf").write_text("edited after intake", encoding="utf-8")
        res = self.run_to(store, 3, run_id="r2")
        self.assertEqual([r.status for r in res.results], ["ok", "blocked"])
        self.assertEqual(res.summary["stopped_at"], 2)
        finding = res.results[1].findings[0]
        self.assertEqual((finding["field"], finding["value"], finding["clause"]), ("inputs/plans/a1.dxf", "changed", "project criterion IM-01"))
        self.assertEqual(finding["id"], "F-0001")
        state = store.read_state()
        self.assertEqual((state["status"], state["stages"][-1]["status"]), ("blocked", "blocked"))
        self.assertEqual(state["open_findings"], res.results[1].findings)
        self.assertIn("stage 2 requirements | blocked | 1 input file(s) changed since intake", store.read_progress())

    def test_stages_after_intake_do_not_run_on_inputs_that_were_never_frozen(self):
        store = self.new_store()
        res = run(self.context(store), run_id="r1", clock=CLOCK, stages=STAGES[1:])
        self.assertEqual([r.status for r in res.results], ["blocked"])
        self.assertEqual(res.results[0].findings[0]["value"], "not frozen")
        self.assertEqual(store.read_state()["status"], "blocked")

    def test_stage_1_failure_does_not_freeze_or_write_a_profile(self):
        store = self.new_store()
        bad = PipelineContext(answers={"project_code": "X"}, store=store)
        res = run(bad, run_id="r1", clock=CLOCK)
        self.assertEqual(res.results[0].status, "blocked")
        self.assertFalse(store.is_frozen())
        self.assertEqual(store.read_profile()["status"], "template")
        self.assertEqual(store.read_state()["status"], "blocked")

    def test_two_runs_with_the_same_run_id_and_clock_give_identical_bytes(self):
        trees = []
        for name in ("one", "two"):
            store = self.new_store(name)
            self.run_to(store, 4)
            trees.append(tree_bytes(store.root))
        self.assertEqual(trees[0], trees[1])
        self.assertIn("ssot/stage_01_intake.json", trees[0])
        self.assertTrue(all(b"\r" not in data for data in trees[0].values()))
        self.assertTrue(all(data.endswith(b"\n") for path, data in trees[0].items() if not path.startswith("inputs/")))

    def test_no_temp_files_remain_after_a_run(self):
        store = self.new_store()
        self.run_to(store, 4)
        self.assertEqual([p.name for p in store.root.rglob("*.tmp")], [])

    def test_the_results_equal_a_run_without_a_store(self):
        store = self.new_store()
        with_store = self.run_to(store, 4)
        plain_inputs = self.tmp() / "inputs" / "plans"
        plain_inputs.mkdir(parents=True)
        (plain_inputs / "a1.dxf").write_text("plan", encoding="utf-8")
        ctx = PipelineContext(answers=ANSWERS, inputs_dir=str(plain_inputs.parent), load_list_path=self.loads_path())
        without = run(ctx, stop_after=4, run_id="r1", clock=CLOCK)
        self.assertEqual([r.to_dict() for r in with_store.results], [r.to_dict() for r in without.results])
        self.assertEqual(with_store.summary, without.summary)

    def test_without_a_store_nothing_is_written_and_work_dir_stays_unset(self):
        ctx = PipelineContext(answers=ANSWERS, load_list_path=self.loads_path())
        run(ctx, stop_after=3, run_id="r1", clock=CLOCK)
        self.assertIsNone(ctx.work_dir)
        self.assertIsNone(ctx.store)


if __name__ == "__main__":
    unittest.main()
