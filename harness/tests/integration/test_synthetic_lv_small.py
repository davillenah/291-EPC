"""MIG-3X: the synthetic project `synthetic_lv_small` runs from the intake answers to `deliverables/` through the real `epc` CLI, with complete manifests.

Needs the engine packages on PYTHONPATH (the gate's `harness-tests` environment has them). Everything is invented data (see the project's README);
the expected values are never written here: the tests check that things exist, validate and agree with each other (hashes, schemas, statuses).
"""
import json
import unittest
from pathlib import Path

import synthetic_lv as S

from disciplines.electrical_lv.intake.schema_check import load_schema, validate
from disciplines.electrical_lv.pipeline import STAGES
from epc_platform.events import EventLog

DOCUMENTS = ("calculation_memo", "project_summary", "terminal_block_list", "boq", "datasheets", "rfq", "design_basis", "descriptive_report")
MANIFEST_KEYS = ("transmittal", "title", "revision", "pipeline_run_id", "inputs", "engines", "normative_profile", "files", "findings",
                 "review_status", "signed", "superseded_signature", "supersedes", "superseded_by")
# The clean run is expected to report these findings and no others (rule id or clause -> severity). Every one is a `note`: the engine assumptions of
# stage 6 (the transformer rating convention) and CC-R00 (the minimum short-circuit current is checked only through its invariants).
EXPECTED_FINDINGS = {("engine assumption", "note"): 4, ("project criterion CC-R00", "note"): 1}


def all_findings(run):
    return [f for r in run["results"] for f in r["findings"]]


class SyntheticRunCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proj = S.SyntheticRun().start()
        cls.addClassCleanup(cls.proj.cleanup)
        cls.code, cls.env = cls.proj.run_result
        cls.result = cls.env["data"]["run"]
        cls.root = cls.proj.project


class RunCompletes(SyntheticRunCase):
    def test_the_project_files_validate(self):
        self.assertEqual(self.proj.init_result[0], 0)
        self.assertEqual((self.code, self.env["ok"]), (0, True))
        for name in ("intake_answers.json", "loads.json"):
            schema = {"intake_answers.json": "intake_answers.schema.json", "loads.json": "load_list.schema.json"}[name]
            self.assertEqual(validate(S.read_json(S.GOLDEN / name), load_schema(schema)), [], name)

    def test_all_12_stages_ran_and_are_ok(self):
        self.assertEqual(len(STAGES), 12)
        self.assertEqual([r["stage"] for r in self.result["results"]], list(range(1, 13)))
        self.assertEqual([r["status"] for r in self.result["results"]], ["ok"] * 12)
        self.assertEqual(self.result["summary"]["by_status"], {"ok": 12})
        self.assertEqual((self.result["summary"]["ok"], self.result["summary"]["not_available"], self.result["summary"]["stopped_at"]), (True, [], None))
        self.assertEqual(self.env["data"]["workflow_state"], "draft_ready")

    def test_status_after_the_run(self):
        code, env = S.envelope(self.proj.root, "status", S.CODE, *S.ORCHESTRATOR)
        self.assertEqual((code, env["ok"]), (0, True))
        data = env["data"]
        self.assertEqual((data["workflow"]["state"], data["state"]["status"], len(data["state"]["stages"])), ("draft_ready", "completed", 12))
        self.assertTrue(data["audit"]["chain_intact"])

    def test_findings_are_exactly_the_expected_notes(self):
        found = {}
        for f in all_findings(self.result):
            key = (f["clause"], f["severity"])
            found[key] = found.get(key, 0) + 1
        self.assertEqual(found, EXPECTED_FINDINGS)
        calc_check = [r for r in self.result["results"] if r["stage"] == 9][0]
        self.assertEqual(sum(calc_check["outputs"]["by_severity"][s] for s in ("blocking", "major", "minor")), 0)
        package = [r for r in self.result["results"] if r["stage"] == 12][0]
        self.assertEqual(package["outputs"]["calc_check"]["findings_count"], 0)


class ProjectFilesAreRecorded(SyntheticRunCase):
    def test_profile_and_state_validate_against_the_schemas(self):
        profile, state = S.read_json(self.root / ".epc" / "project_profile.json"), S.read_json(self.root / ".epc" / "master_project_state.json")
        self.assertEqual(validate(profile, load_schema("project_profile.schema.json")), [])
        self.assertEqual(validate(state, load_schema("master_project_state.schema.json")), [])
        self.assertEqual((profile["project_code"], state["status"], state["pipeline_run_id"]), (S.CODE, "completed", S.RUN_ID))

    def test_one_ssot_file_per_stage_equals_the_stage_result(self):
        for stage in STAGES:
            path = self.root / ".epc" / "ssot" / f"stage_{stage.number:02d}_{stage.spec.slug}.json"
            self.assertTrue(path.is_file(), path.name)
            self.assertEqual(S.read_json(path), json.loads(json.dumps(self.result["results"][stage.number - 1])), path.name)
        self.assertTrue((self.root / ".epc" / "ssot" / "inputs_manifest.json").is_file())

    def test_progress_log_has_one_line_per_stage(self):
        lines = (self.root / ".epc" / "epc_progress.txt").read_text(encoding="utf-8").splitlines()
        stage_lines = [line for line in lines if f"run {S.RUN_ID} | stage" in line]
        self.assertEqual(len(stage_lines), 12)
        self.assertTrue(all(" | ok | " in line for line in stage_lines))

    def test_the_event_log_chain_verifies(self):
        log = EventLog.for_project(self.root, S.clock)
        self.assertEqual(log.verify(), [])
        records = log.read()
        self.assertGreater(len(records), 5)
        self.assertEqual([r["seq"] for r in records], list(range(1, len(records) + 1)))
        self.assertEqual({r["result"] for r in records} - {"allowed", "ok"}, set())

    def test_the_inputs_are_frozen_and_hashed(self):
        manifest = S.read_json(self.root / ".epc" / "ssot" / "inputs_manifest.json")
        paths = sorted(f["path"] for f in manifest["files"])
        self.assertEqual(paths, ["engine_inputs.json", "intake_answers.json", "loads/loads.json"])
        for entry in manifest["files"]:
            self.assertEqual(S.sha256_file(self.root / "inputs" / entry["path"]), entry["sha256"], entry["path"])


class Deliverables(SyntheticRunCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manifests = {p.name: S.read_json(p) for p in cls.proj.manifests()}
        cls.package = cls.proj.ssot("stage_12_package_issue.json")
        cls.documents = {d["name"]: d for d in cls.proj.ssot("stage_11_documents.json")["outputs"]["documents"]}
        cls.sources = {row["name"]: row["source"] for row in cls.package["outputs"]["transmittal"]["files"]}

    def test_the_expected_summary_matches_what_was_produced(self):
        expected = S.read_json(S.GOLDEN / "expected_summary.json")
        self.assertEqual(sorted(self.manifests), [expected["transmittal"] + ".manifest.json"])
        (manifest,) = self.manifests.values()
        names = sorted(f["name"] for f in manifest["files"])
        self.assertEqual(len(names), expected["file_count"])
        for name in expected["documents"]:
            self.assertIn(name, names)
        for sheet in expected["drawings"]["sheets"]:
            self.assertIn(sheet, names)
        self.assertEqual(sorted(self.documents), sorted(DOCUMENTS))
        for name in self.documents:
            self.assertIn(name, expected["documents"])
        self.assertEqual(manifest["transmittal"], expected["transmittal"])
        self.assertEqual(self.package["outputs"]["revision"], expected["revision"])

    def test_every_manifest_validates_and_is_complete(self):
        schema = load_schema("deliverable_manifest.schema.json")
        for name, manifest in self.manifests.items():
            with self.subTest(manifest=name):
                self.assertEqual(validate(manifest, schema), [])
                self.assertEqual(sorted(manifest), sorted(MANIFEST_KEYS))
                self.assertTrue(manifest["transmittal"] and manifest["title"])
                self.assertEqual((manifest["revision"], manifest["pipeline_run_id"]), ("R0", S.RUN_ID))
                self.assertEqual(manifest["review_status"], "draft")
                self.assertEqual([manifest[k] for k in ("signed", "superseded_signature", "supersedes", "superseded_by")], [None] * 4)
                self.assertEqual(name, manifest["transmittal"] + ".manifest.json")

    def test_manifest_inputs_engines_norms_and_findings_are_filled(self):
        frozen = {f["path"]: f["sha256"] for f in self.proj.ssot("inputs_manifest.json")["files"]}
        for name, manifest in self.manifests.items():
            with self.subTest(manifest=name):
                self.assertEqual({i["path"]: i["sha256"] for i in manifest["inputs"]}, frozen)
                for item in manifest["inputs"]:
                    self.assertEqual(S.sha256_file(self.root / "inputs" / item["path"]), item["sha256"])
                self.assertTrue(manifest["engines"] and all(e["name"] and e["version"] for e in manifest["engines"]))
                records = manifest["normative_profile"]["norm_records"]
                self.assertTrue(records and manifest["normative_profile"]["revisions"])
                self.assertTrue(all(r["id"] and r["review_status"] in ("verified", "pending review", "rejected") for r in records))
                self.assertTrue(any(r["review_status"] != "verified" for r in records))
                self.assertEqual(sorted((f["clause"], f["severity"]) for f in manifest["findings"]),
                                 sorted(k for k, n in EXPECTED_FINDINGS.items() for _ in range(n)))

    def test_no_manifest_is_approved_and_every_unreviewed_record_keeps_it_a_draft(self):
        for manifest in self.manifests.values():
            self.assertNotEqual(manifest["review_status"], "approved_for_construction")
            self.assertEqual(manifest["review_status"], "draft")

    def test_every_file_hash_equals_its_manifest_entry(self):
        (manifest,) = self.manifests.values()
        drawings = 0
        for entry in manifest["files"]:
            if entry["path"]:
                drawings += 1
                rel = Path(self.sources[entry["name"]])
                self.assertEqual(rel.suffix, ".dxf")
                self.assertEqual(S.sha256_file(self.root / ".epc" / "runs" / S.RUN_ID / rel), entry["sha256"], entry["name"])
                self.assertEqual(S.sha256_file(self.root / "deliverables" / manifest["transmittal"] / entry["path"]), entry["sha256"], entry["name"])
            else:
                self.assertEqual(self.documents[entry["name"]]["sha256"], entry["sha256"], entry["name"])
        self.assertEqual(drawings, 2)

    def test_the_transmittal_lists_every_file_with_its_hash(self):
        (manifest,) = self.manifests.values()
        transmittal = self.package["outputs"]["transmittal"]
        self.assertEqual({r["name"]: r["sha256"] for r in transmittal["files"]}, {f["name"]: f["sha256"] for f in manifest["files"]})
        self.assertEqual((transmittal["id"], transmittal["review_status"], transmittal["revision"]), (manifest["transmittal"], "draft", "R0"))
        self.assertTrue((self.root / transmittal["manifest"]).is_file())

    def test_drawing_files_exist_and_are_listed_by_stage_10(self):
        stage10 = self.proj.ssot("stage_10_drawings.json")["outputs"]
        names = {f["path"] for f in stage10["files"]}
        for sheet in S.read_json(S.GOLDEN / "expected_summary.json")["drawings"]["sheets"]:
            self.assertIn(f"{sheet}.dxf", names)
        for item in stage10["files"]:
            path = self.root / ".epc" / "runs" / S.RUN_ID / stage10["directory"] / item["path"]
            self.assertEqual(S.sha256_file(path), item["sha256"], item["path"])

    def test_the_unreviewed_norm_records_are_reported_not_hidden(self):
        records = self.package["outputs"]["norm_records"]
        self.assertGreater(records["not_verified"], 0)
        self.assertLessEqual(records["not_verified"], records["listed"])


if __name__ == "__main__":
    unittest.main()
