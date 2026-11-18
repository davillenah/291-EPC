"""MIG-32: the transmittal manifest (PRD section 13), the D21 approval block, supersession and stage 12 (package issue).

Needs the engine packages on PYTHONPATH (the gate's `harness-tests` environment has them). Synthetic data in temp folders only; nothing is
written inside the repository's projects/ tree. The signature used in the supersede tests is synthetic test data, not a real signer.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

import test_pipeline_wiring as W
from test_ssot_wired_pipeline import ANSWERS

from disciplines.electrical_lv import manifest as M
from disciplines.electrical_lv import naming as N
from disciplines.electrical_lv import norm_records as NR
from disciplines.electrical_lv.manifest import sha256_file
from disciplines.electrical_lv.intake.profile import build_profile
from disciplines.electrical_lv.intake.schema_check import load_schema, validate
from disciplines.electrical_lv.pipeline import STAGES, PipelineContext, run
from disciplines.electrical_lv.store import ProjectStore, StoreError, dumps

CLOCK = lambda: "2026-01-01T00:00:00Z"  # noqa: E731
REPO = Path(__file__).resolve().parents[3]
SCHEMA = "deliverable_manifest.schema.json"
INPUTS = {"algorithm": "sha256", "files": [{"path": "b.txt", "sha256": "b" * 64}, {"path": "a.txt", "sha256": "a" * 64}], "manifest_sha256": "0" * 64}
CALLS = [{"engine": "calculation/aea90364", "function": "epc_aea90364.board_memo.build", "version": "1.6.0"},
         {"engine": "calculation/aea90364", "function": "epc_aea90364.aea_pipeline.calculate", "version": "1.6.0"},
         {"engine": "cad/drawing", "function": "epc_drawing.board_design.design", "version": "0.1.0"}]
PROFILE = {"jurisdiction": "AR", "revisions": {"90364-7-771": "2006", "90364-7-770": "2017", "90364-7-701": "2012", "90364-7-722": "2018", "parts_4_and_5": None}}
SIGNATURE = {"signer": "Synthetic Signer", "date": "2026-01-02"}
ALL_VERIFIED = lambda packages: [{"id": "x.1", "review_status": "verified"}, {"id": "x.2", "review_status": "verified"}]  # noqa: E731
ONE_PENDING = lambda packages: [{"id": "x.1", "review_status": "verified"}, {"id": "x.2", "review_status": "pending review"}]  # noqa: E731


FILES = [{"name": "SLD", "title": "Drawing SLD", "path": "SLD.dxf", "sha256": "c" * 64}]


def build(**changes):
    args = dict(transmittal="TR-001", title="Transmittal TR-001", revision="R0", run_id="r1", inputs_manifest=INPUTS, engine_calls=CALLS,
                normative_profile=PROFILE, findings=[], files=FILES, norm_reader=ALL_VERIFIED)
    args.update(changes)
    return M.build_manifest(**args)


class BuildTests(unittest.TestCase):
    def test_a_built_manifest_is_valid_and_has_the_prd_fields(self):
        m = build()
        self.assertEqual(validate(m, load_schema(SCHEMA)), [])
        for key in ("transmittal", "title", "revision", "pipeline_run_id", "inputs", "engines", "normative_profile", "files", "findings",
                    "review_status", "signed", "supersedes", "superseded_by"):
            self.assertIn(key, m)

    def test_the_files_are_sorted_by_name_and_a_document_without_a_file_has_a_null_path(self):
        doc = {"name": "memo", "title": "Memo", "path": None, "sha256": "d" * 64}
        m = build(files=[doc] + FILES)
        self.assertEqual([f["name"] for f in m["files"]], ["SLD", "memo"])
        self.assertIsNone(m["files"][1]["path"])
        self.assertEqual(validate(m, load_schema(SCHEMA)), [])

    def test_a_file_hash_equals_sha256_of_its_bytes(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "x.dxf"
            f.write_bytes(b"abc")
            self.assertEqual(sha256_file(f), hashlib.sha256(b"abc").hexdigest())

    def test_a_transmittal_needs_files_and_unique_names(self):
        with self.assertRaises(M.ManifestError):
            build(files=[])
        with self.assertRaises(M.ManifestError):
            build(files=FILES + FILES)

    def test_inputs_come_from_the_frozen_manifest_sorted(self):
        self.assertEqual(build()["inputs"], [{"path": "a.txt", "sha256": "a" * 64}, {"path": "b.txt", "sha256": "b" * 64}])
        with self.assertRaises(M.ManifestError):
            build(inputs_manifest=None)

    def test_engines_and_versions_come_from_the_recorded_calls(self):
        self.assertEqual(build()["engines"], [{"name": "cad/drawing", "version": "0.1.0"}, {"name": "calculation/aea90364", "version": "1.6.0"}])
        bad = CALLS + [{"engine": "x/y", "function": "epc_y.f", "version": None}]
        with self.assertRaises(M.ManifestError):
            build(engine_calls=bad)

    def test_the_profile_revisions_are_copied_and_records_come_from_the_reader(self):
        m = build()
        self.assertEqual(m["normative_profile"]["revisions"], PROFILE["revisions"])
        self.assertEqual([r["id"] for r in m["normative_profile"]["norm_records"]], ["x.1", "x.2"])

    def test_the_reader_receives_the_engine_packages(self):
        seen = []
        build(norm_reader=lambda packages: seen.append(packages) or [])
        self.assertEqual(seen, [["epc_aea90364", "epc_drawing"]])

    def test_the_default_status_is_draft_and_signed_is_null(self):
        m = build()
        self.assertEqual((m["review_status"], m["signed"], m["superseded_signature"], m["supersedes"], m["superseded_by"]), ("draft", None, None, None, None))

    def test_a_manifest_is_deterministic(self):
        self.assertEqual(dumps(build()).encode(), dumps(build()).encode())


class ApprovalTests(unittest.TestCase):
    def test_approval_is_possible_when_every_record_is_verified(self):
        m = build(review_status="approved_for_construction")
        self.assertEqual(m["review_status"], "approved_for_construction")

    def test_approval_is_blocked_by_one_unreviewed_record(self):
        with self.assertRaises(M.ApprovalBlocked) as cm:
            build(review_status="approved_for_construction", norm_reader=ONE_PENDING)
        self.assertIn("x.2", str(cm.exception))

    def test_approval_is_blocked_with_the_real_register(self):
        with self.assertRaises(M.ApprovalBlocked):
            build(review_status="approved_for_construction", norm_reader=NR.read_norm_records)

    def test_for_review_and_draft_are_allowed_with_unreviewed_records(self):
        for status in ("draft", "for_review"):
            self.assertEqual(build(review_status=status, norm_reader=ONE_PENDING)["review_status"], status)

    def test_the_schema_also_refuses_an_approved_manifest_with_an_unreviewed_record(self):
        m = build(norm_reader=ONE_PENDING)
        m["review_status"] = "approved_for_construction"
        self.assertTrue(validate(m, load_schema(SCHEMA)))

    def test_the_schema_refuses_unknown_fields_and_statuses(self):
        for change in ({"extra": 1}, {"review_status": "signed_off"}, {"files": []}):
            m = build()
            m.update(change)
            with self.subTest(change=change):
                self.assertTrue(validate(m, load_schema(SCHEMA)))


class NormRecordsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(REPO / "harness" / "tools" / "build"))
        try:
            import norm_register
            cls.reg = norm_register.Register(REPO)
        finally:
            sys.path.remove(str(REPO / "harness" / "tools" / "build"))
        cls.records = NR.read_norm_records(["epc_aea90364"])

    def test_the_ids_equal_the_ones_of_the_register_tool(self):
        hand = {r["id"] for rel, r in self.reg.records if "/calculation/aea90364/" in rel}
        auto = {a["id"] for a in self.reg.auto if a["engine"] == "aea90364"}
        self.assertTrue(hand and auto)
        self.assertEqual({r["id"] for r in self.records}, hand | auto)

    def test_the_review_status_follows_the_register(self):
        got = {r["id"]: r["review_status"] for r in self.records}
        for a in self.reg.auto:
            if a["engine"] == "aea90364":
                self.assertEqual(got[a["id"]] == "verified", a["review"] == "approved", a["id"])
        for rel, r in self.reg.records:
            if "/calculation/aea90364/" in rel and r["status"] == "pending":
                approved = self.reg.review.get(r["review_point"], {}).get("status") == "approved"
                self.assertEqual(got[r["id"]] == "verified", approved, r["id"])

    def test_nothing_is_invented_for_an_unknown_package(self):
        self.assertEqual(NR.read_norm_records(["epc_does_not_exist"]), [])

    def test_the_states_are_in_the_vocabulary(self):
        self.assertLessEqual({r["review_status"] for r in self.records}, {"verified", "pending review", "rejected"})


class SupersedeTests(unittest.TestCase):
    def test_the_previous_manifest_is_marked_and_its_signature_moved(self):
        old = build()
        old["signed"] = dict(SIGNATURE)
        new = build(revision="R1", transmittal="TR-002")
        old2, new2 = M.supersede(old, new)
        self.assertEqual((old2["superseded_by"], old2["signed"], old2["superseded_signature"]), ("TR-002/R1", None, SIGNATURE))
        self.assertEqual((new2["supersedes"], new2["signed"]), ("TR-001/R0", None))
        self.assertIsNone(old["superseded_by"])      # inputs untouched
        self.assertEqual(M.check(old2) + M.check(new2), [])

    def test_refusals(self):
        with self.assertRaises(M.ManifestError):
            M.supersede(build(), build())
        with self.assertRaises(M.ManifestError):
            M.supersede(build(), build(revision="R1"))                     # a transmittal is not superseded by itself
        with self.assertRaises(M.ManifestError):
            M.supersede(build(), build(transmittal="TR-002"))              # same revision
        old2, _ = M.supersede(build(), build(revision="R1", transmittal="TR-002"))
        with self.assertRaises(M.ManifestError):
            M.supersede(old2, build(revision="R2", transmittal="TR-003"))


class StoreManifestTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.store = ProjectStore(Path(holder.name) / "proj")
        self.store.init_from_template()

    def test_writes_need_the_token(self):
        with self.assertRaises(PermissionError):
            self.store.write_manifest(None, build())
        with self.store.pipeline_session("t1") as token:
            pass
        with self.assertRaises(PermissionError):
            self.store.write_manifest(token, build())      # the session is over

    def test_a_manifest_is_written_atomically_in_the_manifests_folder(self):
        with self.store.pipeline_session("t1") as token:
            rel = self.store.write_manifest(token, build())
        self.assertEqual(rel, ".epc/manifests/TR-001.manifest.json")
        path = self.store.root / rel
        self.assertEqual(path.read_bytes(), dumps(build()).encode("utf-8"))
        self.assertEqual([p.name for p in path.parent.iterdir()], [path.name])
        self.assertEqual(self.store.read_manifests("TR-001"), [(rel, build())])

    def test_an_invalid_or_escaping_manifest_is_refused(self):
        bad_rev = build()
        bad_rev["revision"] = "../x"
        bad_id = build()
        bad_id["transmittal"] = "a/b"
        with self.store.pipeline_session("t1") as token:
            for m in (bad_rev, bad_id, {"title": "x"}):
                with self.assertRaises(StoreError):
                    self.store.write_manifest(token, m)
        self.assertEqual(self.store.read_manifests(), [])

    def test_a_signed_manifest_is_not_overwritten(self):
        signed = build()
        signed["signed"] = dict(SIGNATURE)
        with self.store.pipeline_session("t1") as token:
            self.store.write_manifest(token, signed)
            with self.assertRaises(StoreError):
                self.store.write_manifest(token, build())
        self.assertEqual(self.store.read_manifests()[0][1]["signed"], SIGNATURE)

    def test_update_only_marks_a_manifest_as_superseded(self):
        old = build()
        old["signed"] = dict(SIGNATURE)
        marked, _ = M.supersede(old, build(revision="R1", transmittal="TR-002"))
        with self.store.pipeline_session("t1") as token:
            self.store.write_manifest(token, old)
            self.store.update_manifest(token, marked)
            stored = self.store.read_manifests()[0][1]
            self.assertEqual((stored["signed"], stored["superseded_signature"], stored["superseded_by"]), (None, SIGNATURE, "TR-002/R1"))
            tampered = copy.deepcopy(marked)
            tampered["files"][0]["sha256"] = "e" * 64
            dropped = copy.deepcopy(marked)
            dropped["superseded_signature"] = None
            reset = copy.deepcopy(marked)
            reset["superseded_by"] = "TR-002/R9"
            for bad in (tampered, dropped, reset):
                with self.assertRaises(StoreError):
                    self.store.update_manifest(token, bad)

    def test_update_cannot_create_or_edit_a_signature(self):
        with self.store.pipeline_session("t1") as token:
            self.store.write_manifest(token, build())
            forged = build()
            forged["signed"] = dict(SIGNATURE)
            with self.assertRaises(StoreError):
                self.store.update_manifest(token, forged)
            with self.assertRaises(StoreError):
                self.store.update_manifest(token, build(transmittal="TR-009"))     # does not exist

    def test_a_deliverable_file_is_copied_into_its_transmittal_folder_and_a_signed_one_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "a.dxf"
            src.write_bytes(b"abc")
            with self.store.pipeline_session("t1") as token:
                sha = self.store.copy_deliverable(token, src, "deliverables/TR-001/a.dxf")
                self.assertEqual((self.store.root / "deliverables/TR-001/a.dxf").read_bytes(), b"abc")
                self.assertEqual(sha, sha256_file(src))
                for bad in ("a.dxf", "deliverables/R0/a.dxf", "deliverables/TR-001"):
                    with self.assertRaises(StoreError):
                        self.store.copy_deliverable(token, src, bad)
                signed = build()
                signed["signed"] = dict(SIGNATURE)
                self.store.write_manifest(token, signed)
                with self.assertRaises(StoreError):
                    self.store.copy_deliverable(token, src, "deliverables/TR-001/a.dxf")


def wired_run(store, revision="R0", run_id="r1", **changes):
    ctx = W.context(profile=build_profile(ANSWERS), store=store)
    ctx.revision = revision
    for key, value in changes.items():
        setattr(ctx, key, value)
    return ctx, run(ctx, run_id=run_id, clock=CLOCK)


def new_store(folder, name="proj"):
    store = ProjectStore(Path(folder) / name)
    store.init_from_template()
    return store


def without_dxf_hash(manifest):
    """The drawing engine stamps the current time into DXF files, so their hash (in the manifest's `files`) changes between runs."""
    out = copy.deepcopy(manifest)
    for f in out["files"]:
        if (f["path"] or "").endswith(".dxf"):
            f["sha256"] = None
    return out


def file_names(store):
    return sorted(f["name"] for _, m in store.read_manifests() for f in m["files"])


class PackageIssueStageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.holder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.holder.cleanup)
        cls.store = new_store(cls.holder.name)
        cls.ctx, cls.res = wired_run(cls.store)
        cls.stage = cls.res.results[11]

    def stored(self):
        return dict(self.store.read_manifests())

    def test_stage_12_ran_and_the_other_pending_stages_are_unchanged(self):
        self.assertEqual(self.stage.status, "ok", self.stage.message)
        self.assertEqual(self.res.summary["not_available"], [4])
        self.assertTrue(STAGES[11].wired)

    def test_one_valid_draft_manifest_covers_every_drawing_file_and_document(self):
        stored = self.stored()
        self.assertEqual(list(stored), [".epc/manifests/TR-001.manifest.json"])
        m = stored[".epc/manifests/TR-001.manifest.json"]
        self.assertEqual(m["transmittal"], "TR-001")
        self.assertEqual(sorted(f["name"] for f in m["files"]), sorted(["calculation_memo", "descriptive_report", "design_basis", "project_summary", "terminal_block_list", "SLD_TEST-001", "SLD_TEST-001_TABLA"]))
        self.assertEqual(M.check(m), [])
        self.assertEqual((m["review_status"], m["signed"], m["superseded_by"], m["pipeline_run_id"]), ("draft", None, None, "r1"))

    def test_the_stage_output_equals_what_was_written(self):
        outs = {i["path"]: i["manifest"] for i in self.stage.outputs["manifests"]}
        self.assertEqual(outs, self.stored())
        self.assertEqual(self.store.read_ssot("stage_12_package_issue.json")["outputs"]["transmittal"], self.stage.outputs["transmittal"])

    def test_drawing_files_are_copied_to_the_transmittal_folder_and_hashed(self):
        (m,) = self.stored().values()
        drawings = [f for f in m["files"] if f["path"]]
        self.assertEqual(len(drawings), 2)
        for f in drawings:
            run_file = self.store.root / ".epc" / "runs" / "r1" / "drawings" / "TEST-001" / "out" / Path(f["path"]).name
            copy_file = self.store.root / "deliverables" / "TR-001" / f["path"]
            self.assertEqual(f["sha256"], sha256_file(run_file))
            self.assertEqual(f["sha256"], sha256_file(copy_file))
        self.assertEqual(sorted(p.name for p in (self.store.root / "deliverables" / "TR-001").iterdir()), ["01_SLD"])
        self.assertEqual(sorted(f["path"] for f in drawings), ["01_SLD/SLD_TEST-001.dxf", "01_SLD/SLD_TEST-001_TABLA.dxf"])

    def test_document_entries_carry_the_hash_stage_11_recorded_and_no_path(self):
        recorded = {d["name"]: d["sha256"] for d in self.res.results[10].outputs["documents"]}
        (m,) = self.stored().values()
        docs = [f for f in m["files"] if not f["path"]]
        self.assertEqual(len(docs), 5)
        for f in docs:
            self.assertEqual(f["sha256"], recorded[f["name"]])

    def test_inputs_engines_and_profile_come_from_the_run(self):
        frozen = self.store.read_ssot("inputs_manifest.json")
        calls = {(c["engine"], c["version"]) for r in self.res.results for c in r.engine_calls}
        for m in self.stored().values():
            self.assertEqual(m["inputs"], [{"path": f["path"], "sha256": f["sha256"]} for f in frozen["files"]])
            self.assertEqual({(e["name"], e["version"]) for e in m["engines"]}, calls)
            self.assertEqual(m["normative_profile"]["revisions"], self.ctx.profile["normative_profile"]["revisions"])
            self.assertTrue(m["normative_profile"]["norm_records"])
            self.assertEqual(m["findings"], [f for r in self.res.results[:15] for f in r.findings])

    def test_unreviewed_records_are_listed_and_the_transmittal_signs_nothing(self):
        info = self.stage.outputs["norm_records"]
        self.assertGreater(info["not_verified"], 0)
        t = self.stage.outputs["transmittal"]
        self.assertEqual((t["id"], t["review_status"], t["revision"], len(t["files"])), ("TR-001", "draft", "R0", 7))
        self.assertNotIn("signed", json.dumps(t))
        self.assertEqual([t["manifest"]], sorted(self.stored()))

    def test_it_never_approves(self):
        for m in self.stored().values():
            self.assertTrue(any(r["review_status"] != "verified" for r in m["normative_profile"]["norm_records"]))
            self.assertNotEqual(m["review_status"], "approved_for_construction")

    def test_a_changed_drawing_file_blocks_the_stage(self):
        file = self.store.root / ".epc" / "runs" / "r1" / "drawings" / "TEST-001" / "out" / "SLD_TEST-001.dxf"
        original = file.read_bytes()
        self.addCleanup(file.write_bytes, original)
        file.write_bytes(original + b"0\n")
        res = STAGES[11].run(self.ctx)
        self.assertEqual((res.status, res.outputs), ("blocked", {}))
        self.assertIn("changed after stage 10", res.message)

    def test_without_a_store_or_without_deliverables_it_is_not_available(self):
        ctx = W.context()
        run(ctx, stop_after=11, run_id="x")
        res = STAGES[11].run(ctx)
        self.assertEqual((res.status, res.outputs, res.reason), ("not_available", {}, "no_store"))
        self.assertIn("no project store", res.message)
        empty = PipelineContext(store=self.store, profile=self.ctx.profile)
        empty.results = {}
        res = STAGES[11].run(empty)
        self.assertEqual((res.status, res.outputs, res.reason), ("not_available", {}, "no_deliverables"))

    def test_a_bad_revision_label_blocks(self):
        ctx = W.context(profile=build_profile(ANSWERS), store=self.store)
        ctx.results = dict(self.ctx.results)
        ctx.pipeline_run_id = "r1"
        ctx.work_dir = self.ctx.work_dir
        ctx.revision = "../R1"
        res = STAGES[11].run(ctx)
        self.assertEqual(res.status, "blocked")


CODE = "2026-ES-HNDA-3085"
NAMES = {f"SLD_{CODE}": {"type": "SLD", "number": 1, "description": "main_distribution_board"},
         f"SLD_{CODE}_TABLA": {"type": "SLD", "number": 1, "description": "main_distribution_board", "page": 2},
         "calculation_memo": {"type": "CAL", "number": 1, "description": "feeder_sizing_calculation"},
         "project_summary": {"type": "RPT", "number": 1, "description": "project_summary"},
         "terminal_block_list": {"type": "LST", "number": 1, "description": "terminal_block_list"},
         "descriptive_report": {"type": "RPT", "number": 2, "description": "descriptive_report"},
         "design_basis": {"type": "RPT", "number": 3, "description": "design_basis"}}


def named_run(folder, names=NAMES, code=CODE):
    store = new_store(folder)
    profile = build_profile(ANSWERS)
    profile["project_code"] = code
    ctx = W.context(profile=profile, store=store)
    ctx.revision = "R0"
    ctx.engine_inputs["deliverable_names"] = copy.deepcopy(names)
    return store, run(ctx, run_id="r1", clock=CLOCK)


class NamedDeliverablesTests(unittest.TestCase):
    """The files of a transmittal are named `<code>_<description>`; plans go in a folder with one file per page."""

    def test_drawings_get_their_code_folder_and_pages_and_documents_get_a_code(self):
        with tempfile.TemporaryDirectory() as folder:
            store, res = named_run(folder)
            self.assertEqual(res.results[11].status, "ok", res.results[11].message)
            (manifest,) = [m for _, m in store.read_manifests()]
            by_name = {f["name"]: f for f in manifest["files"]}
            stem = f"{CODE}-E-LV-SLD-001_main_distribution_board"
            self.assertEqual(by_name[f"SLD_{CODE}"]["path"], f"01_SLD/{stem}/{stem}_P01.dxf")
            self.assertEqual(by_name[f"SLD_{CODE}_TABLA"]["path"], f"01_SLD/{stem}/{stem}_P02.dxf")
            self.assertEqual(by_name["calculation_memo"]["code"], f"{CODE}-E-LV-CAL-001")
            self.assertIsNone(by_name["calculation_memo"]["path"])
            self.assertEqual(M.check(manifest), [])
            folder_files = sorted(p.relative_to(store.root / "deliverables" / "TR-001").as_posix() for p in (store.root / "deliverables" / "TR-001").rglob("*") if p.is_file())
            self.assertEqual(folder_files, [f"01_SLD/{stem}/{stem}_P01.dxf", f"01_SLD/{stem}/{stem}_P02.dxf"])
            for f in manifest["files"]:
                if f["path"]:
                    self.assertEqual(sha256_file(store.root / "deliverables" / "TR-001" / f["path"]), f["sha256"])
            self.assertTrue(res.results[11].outputs["naming"]["named"])
            self.assertEqual([f["clause"] for f in res.results[11].findings if "CC-D06" in f["clause"] or "CC-F06" in f["clause"]], [])   # the hashes agree with the recorded ones

    def test_a_deliverable_without_a_name_blocks_and_nothing_is_written(self):
        with tempfile.TemporaryDirectory() as folder:
            names = {k: v for k, v in NAMES.items() if k != "design_basis"}
            store, res = named_run(folder, names)
            self.assertEqual(res.results[11].status, "blocked")
            self.assertIn("design_basis: no entry", res.results[11].message)
            self.assertEqual(store.read_manifests(), [])

    def test_a_project_code_that_is_not_aaaa_prov_cli_code_blocks(self):
        with tempfile.TemporaryDirectory() as folder:
            _store, res = named_run(folder, code="TEST-001")
            self.assertEqual(res.results[11].status, "blocked")
            self.assertIn("AAAA-PROVIDER-CLIENT-CODE", res.results[11].message)

    def test_two_deliverables_with_the_same_page_block(self):
        with tempfile.TemporaryDirectory() as folder:
            names = copy.deepcopy(NAMES)
            names[f"SLD_{CODE}_TABLA"]["page"] = 1
            _store, res = named_run(folder, names)
            self.assertEqual(res.results[11].status, "blocked")
            self.assertIn("share the path", res.results[11].message)

    def test_without_names_the_engine_names_are_kept(self):
        with tempfile.TemporaryDirectory() as folder:
            store = new_store(folder)
            ctx, res = wired_run(store)
            self.assertFalse(res.results[11].outputs["naming"]["named"])
            (manifest,) = [m for _, m in store.read_manifests()]
            self.assertTrue(all(f["code"] is None for f in manifest["files"]))


class NamingTests(unittest.TestCase):
    def entry(self, **changes):
        return dict({"type": "SLD", "number": 2, "description": "lighting_distribution"}, **changes)

    def test_code_stem_and_paths(self):
        self.assertEqual(N.document_code(CODE, self.entry()), f"{CODE}-E-LV-SLD-002")
        self.assertEqual(N.document_code(CODE, self.entry(level="LS01", sub="MV")), f"{CODE}-E-MV-SLD-002-LS01")
        self.assertEqual(N.file_path(CODE, self.entry(page=3), ".dxf"), f"{CODE}-E-LV-SLD-002_lighting_distribution/{CODE}-E-LV-SLD-002_lighting_distribution_P03.dxf")
        self.assertEqual(N.file_path(CODE, self.entry(type="CAL"), ".xlsx"), f"{CODE}-E-LV-CAL-002_lighting_distribution.xlsx")

    def test_invalid_entries_are_reported(self):
        for change in ({"type": "XXX"}, {"number": 0}, {"number": "1"}, {"description": "Iluminación"}, {"description": "a" * 41}, {"description": "two  words"},
                       {"level": "L1"}, {"level": "S01"}, {"page": 0}, {"sub": "HV"}, {"extra": 1}):
            with self.subTest(change=change):
                self.assertTrue(N.problems(self.entry(**change)))
        self.assertEqual(N.problems(self.entry(level="L00", page=2)), [])

    def test_every_document_type_of_the_catalog_is_known(self):
        catalog = json.loads((REPO / "harness" / "schemas" / "document-catalog.json").read_text(encoding="utf-8"))
        types = {d["type"] for d in catalog["disciplines"]["electrical"]["documents"]}
        self.assertLessEqual(types, set(N.TYPES))
        self.assertLessEqual(set(N.PAGED_TYPES), set(N.TYPES))

    def test_the_manifest_schema_pattern_accepts_a_generated_code(self):
        file = {"name": "x", "title": "x", "code": N.document_code(CODE, self.entry(level="L01")), "path": None, "sha256": "a" * 64}
        self.assertEqual(validate(build(files=[file]), load_schema(SCHEMA)), [])
        with self.assertRaises(M.ManifestError):
            build(files=[dict(file, code="bad")])


class BillOfQuantitiesManifestTests(unittest.TestCase):
    """MIG-39c: the bill of quantities (no file) gets a draft manifest like the other documents of stage 11, only when stage 11 produced it."""

    def test_a_draft_manifest_for_the_bill_when_it_was_produced(self):
        with tempfile.TemporaryDirectory() as folder:
            store = new_store(folder)
            ctx = W.context(profile=build_profile(ANSWERS), store=store)
            ctx.revision = "R0"
            ctx.engine_inputs["boq"] = {"allowance_pct": 5}
            res = run(ctx, run_id="r1", clock=CLOCK)
            self.assertEqual(res.results[11].status, "ok", res.results[11].message)
            names = file_names(store)
            self.assertIn("boq", names)
            self.assertEqual(len(names), 8)
            (manifest,) = [m for _, m in store.read_manifests()]
            self.assertEqual((M.check(manifest), manifest["review_status"], manifest["signed"]), ([], "draft", None))


class DatasheetsManifestTests(unittest.TestCase):
    """MIG-39d: the datasheets (no file) get a draft manifest like the other documents of stage 11, only when stage 11 produced them."""

    def test_a_draft_manifest_for_the_datasheets_when_they_were_produced(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as catalog:
            W.synthetic_catalog(catalog)
            store = new_store(folder)
            ctx = W.context(profile=build_profile(ANSWERS), store=store)
            ctx.revision = "R0"
            ctx.engine_inputs["datasheets"] = {"catalog_dir": catalog}
            res = run(ctx, run_id="r1", clock=CLOCK)
            self.assertEqual(res.results[11].status, "ok", res.results[11].message)
            names = file_names(store)
            self.assertIn("datasheets", names)
            self.assertEqual(len(names), 8)
            (manifest,) = [m for _, m in store.read_manifests()]
            self.assertEqual((M.check(manifest), manifest["review_status"], manifest["signed"]), ([], "draft", None))


class RfqManifestTests(unittest.TestCase):
    """MIG-39e: the RFQ (no file) gets a draft manifest like the other documents of stage 11, only when stage 11 produced it."""

    def test_a_draft_manifest_for_the_rfq_when_it_was_produced(self):
        with tempfile.TemporaryDirectory() as folder:
            store = new_store(folder)
            ctx = W.context(profile=build_profile(ANSWERS), store=store)
            ctx.revision = "R0"
            ctx.engine_inputs["boq"] = {"allowance_pct": 5}
            ctx.engine_inputs["rfq"] = W.RFQ_TERMS
            res = run(ctx, run_id="r1", clock=CLOCK)
            self.assertEqual(res.results[11].status, "ok", res.results[11].message)
            names = file_names(store)
            self.assertIn("rfq", names)
            self.assertEqual(len(names), 9)
            (manifest,) = [m for _, m in store.read_manifests()]
            self.assertEqual((M.check(manifest), manifest["review_status"], manifest["signed"]), ([], "draft", None))

    def test_no_manifest_when_the_rfq_stays_pending(self):
        with tempfile.TemporaryDirectory() as folder:
            store = new_store(folder)
            ctx = W.context(profile=build_profile(ANSWERS), store=store)
            ctx.revision = "R0"
            ctx.engine_inputs["rfq"] = W.RFQ_TERMS
            run(ctx, run_id="r1", clock=CLOCK)
            self.assertNotIn("rfq", file_names(store))


class DesignBasisManifestTests(unittest.TestCase):
    """MIG-39f: the design basis (no file) gets a draft manifest like the other documents of stage 11."""

    def test_a_draft_manifest_for_the_design_basis(self):
        with tempfile.TemporaryDirectory() as folder:
            store = new_store(folder)
            ctx = W.context(profile=build_profile(ANSWERS), store=store)
            ctx.revision = "R0"
            res = run(ctx, run_id="r1", clock=CLOCK)
            self.assertEqual(res.results[11].status, "ok", res.results[11].message)
            self.assertEqual(file_names(store).count("design_basis"), 1)
            (manifest,) = [m for _, m in store.read_manifests()]
            self.assertEqual((M.check(manifest), manifest["review_status"], manifest["signed"]), ([], "draft", None))


class ReproducibilityTests(unittest.TestCase):
    def test_two_runs_give_the_same_manifest_except_dxf_hashes(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            sa, sb = new_store(a), new_store(b)
            wired_run(sa)
            wired_run(sb)
            ma, mb = dict(sa.read_manifests()), dict(sb.read_manifests())
            self.assertEqual(sorted(ma), sorted(mb))
            for rel in ma:
                self.assertEqual(dumps(without_dxf_hash(ma[rel])), dumps(without_dxf_hash(mb[rel])), rel)
            # the .dxf files are the only difference: the engine writes the current time into them
            self.assertNotEqual(ma, mb)


class RegenerationTests(unittest.TestCase):
    REL = ".epc/manifests/TR-001.manifest.json"

    def sign(self, store, rel):
        signed = store.read_json(rel)
        signed["signed"] = dict(SIGNATURE)                       # synthetic signature of a test
        with store.pipeline_session("t") as token:
            store.write_manifest(token, signed)

    def test_a_new_revision_gets_the_next_transmittal_and_supersedes_the_previous_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = new_store(tmp)
            wired_run(store, "R0", "r1")
            self.sign(store, self.REL)
            _, res = wired_run(store, "R1", "r2")
            self.assertEqual(res.results[11].status, "ok", res.results[11].message)
            after = dict(store.read_manifests())
            self.assertEqual(sorted(after), [self.REL, ".epc/manifests/TR-002.manifest.json"])
            old, new = after[self.REL], after[".epc/manifests/TR-002.manifest.json"]
            self.assertEqual((old["superseded_by"], old["signed"], old["superseded_signature"]), ("TR-002/R1", None, SIGNATURE))
            self.assertEqual((new["supersedes"], new["signed"], new["revision"]), ("TR-001/R0", None, "R1"))
            self.assertEqual(len(res.results[11].outputs["superseded"]), 1)
            self.assertTrue((store.root / "deliverables" / "TR-001").is_dir() and (store.root / "deliverables" / "TR-002").is_dir())
            for m in after.values():
                self.assertEqual(M.check(m), [])

    def test_a_rerun_of_an_unsigned_draft_revision_replaces_it_with_the_same_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = new_store(tmp)
            wired_run(store, "R0", "r1")
            _, res = wired_run(store, "R0", "r2")
            self.assertEqual(res.results[11].status, "ok", res.results[11].message)
            ((rel, m),) = store.read_manifests()
            self.assertEqual((rel, m["transmittal"], m["pipeline_run_id"], m["supersedes"]), (self.REL, "TR-001", "r2", None))

    def test_regenerating_a_signed_revision_in_place_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = new_store(tmp)
            wired_run(store, "R0", "r1")
            self.sign(store, self.REL)
            _, res = wired_run(store, "R0", "r2")
            self.assertEqual(res.results[11].status, "blocked")
            self.assertIn("is signed", res.results[11].message)
            self.assertEqual(store.read_json(self.REL)["signed"], SIGNATURE)


if __name__ == "__main__":
    unittest.main()
