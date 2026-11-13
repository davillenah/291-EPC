"""MIG-3X / MIG-3Z: reproducibility (PRD section 21 criterion 5). The synthetic project, run twice in two separate projects roots with the same run id and the
same injected clock:

* Pinned (`engine_inputs["drawings"]["date"]` given, MIG-3Z): EVERY file is byte-identical, the DXF drawings, `input_for_sld.xlsx` and the four JSON files that embed the
  DXF hashes included (`Pinned` below).
* Not pinned (no drawing date, the default, unchanged): the DXF writer stamps the clock and random GUIDs (ezdxf: creation and update times, `$VERSIONGUID`,
  `$FINGERPRINTGUID`, its metadata markers) and `input_for_sld.xlsx` (a zip with file times) carries the clock, so those files and the hashes (and sizes) that
  embed them (stage 14, stage 16 and the two drawing manifests) differ. Nothing else may differ: the test fails if any other file differs, and it proves that
  the DXF hashes are the ONLY difference inside the files that embed them (`Reproducibility` below).
"""
import json
import unittest

import synthetic_lv as S

from epc_platform.events import EventLog

# Files whose bytes may differ between two runs: the DXF drawings and the xlsx input the drawing engine writes (current time, random GUIDs).
TIME_STAMPED = (".dxf",)
TIME_STAMPED_NAMES = ("input_for_sld.xlsx",)
# Files that carry the SHA-256 of a DXF and therefore differ only in that hash.
EMBED_DXF_HASH = (".epc/ssot/stage_14_drawings.json", ".epc/ssot/stage_16_package_issue.json", ".epc/manifests/TR-001.manifest.json")


def files_of(project):
    return {p.relative_to(project).as_posix(): p for p in sorted(project.rglob("*")) if p.is_file()}


class Reproducibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a, cls.b = S.SyntheticRun().start(), S.SyntheticRun().start()
        cls.addClassCleanup(cls.a.cleanup)
        cls.addClassCleanup(cls.b.cleanup)
        cls.fa, cls.fb = files_of(cls.a.project), files_of(cls.b.project)

    def test_both_runs_completed_with_the_same_run_id(self):
        for proj in (self.a, self.b):
            self.assertEqual(proj.run_result[0], 0)
            self.assertEqual(proj.run_result[1]["data"]["pipeline_run_id"], S.RUN_ID)
            self.assertEqual(proj.run_result[1]["data"]["run"]["summary"]["by_status"], {"ok": 16})

    def test_the_same_files_exist(self):
        self.assertEqual(sorted(self.fa), sorted(self.fb))
        self.assertGreater(len(self.fa), 40)

    def test_only_time_stamped_files_and_the_hashes_that_embed_them_differ(self):
        different = sorted(rel for rel in self.fa if self.fa[rel].read_bytes() != self.fb[rel].read_bytes())
        allowed = {rel for rel in self.fa if rel.endswith(TIME_STAMPED) or rel.rsplit("/", 1)[-1] in TIME_STAMPED_NAMES} | set(EMBED_DXF_HASH)
        self.assertEqual(sorted(set(different) - allowed), [])
        self.assertTrue(any(rel.endswith(".dxf") for rel in different), "the DXF writer is expected to stamp the time; if this fails the gap is closed: pin it")

    def test_everything_that_should_be_identical_is_byte_identical(self):
        for rel in self.fa:
            if rel.endswith(".dxf") or rel in EMBED_DXF_HASH or rel.rsplit("/", 1)[-1] in TIME_STAMPED_NAMES:
                continue
            with self.subTest(file=rel):
                self.assertEqual(self.fa[rel].read_bytes(), self.fb[rel].read_bytes())

    def test_the_named_artifacts_are_identical(self):
        for rel in (".epc/project_profile.json", ".epc/master_project_state.json", ".epc/epc-progress.txt", ".epc/audit/events.jsonl", ".epc/reviews/workflow.json",
                    ".epc/ssot/inputs_manifest.json"):
            self.assertEqual(self.fa[rel].read_bytes(), self.fb[rel].read_bytes(), rel)
        stages = [rel for rel in self.fa if rel.startswith(".epc/ssot/stage_")]
        self.assertEqual(len(stages), 16)
        self.assertEqual(len([rel for rel in self.fa if rel.endswith(".manifest.json")]), 1)
        self.assertEqual(self.a.ssot("stage_15_documents.json"), self.b.ssot("stage_15_documents.json"))

    def test_the_event_logs_are_the_same_hash_chain(self):
        logs = [EventLog.for_project(p.project, S.clock) for p in (self.a, self.b)]
        self.assertEqual([log.verify() for log in logs], [[], []])
        self.assertEqual(logs[0].read(), logs[1].read())
        self.assertEqual(logs[0].last(), logs[1].last())

    def test_the_embedded_dxf_hashes_are_the_only_difference(self):
        for rel in EMBED_DXF_HASH:
            with self.subTest(file=rel):
                one, two = (json.loads(f[rel].read_text(encoding="utf-8")) for f in (self.fa, self.fb))
                self.assertNotEqual(one, two)
                self.assertEqual(S.normalise_dxf_hashes(one), S.normalise_dxf_hashes(two))

    def test_the_dxf_content_differs_only_in_time_and_identifiers(self):
        """The two DXF files of a run differ in a handful of header lines (Julian dates, GUIDs, a dictionary name), never in the drawing itself."""
        for rel in (r for r in self.fa if r.endswith(".dxf")):
            one = self.fa[rel].read_text(encoding="utf-8", errors="replace").splitlines()
            two = self.fb[rel].read_text(encoding="utf-8", errors="replace").splitlines()
            self.assertEqual(len(one), len(two), rel)
            changed = [(x, y) for x, y in zip(one, two) if x != y]
            self.assertLessEqual(len(changed), 12, rel)


PINNED_DATE = "2026-03-04"


class Pinned(unittest.TestCase):
    """The same inputs with the drawing date pinned: nothing differs, not even the DXF files (MIG-3Z)."""

    @classmethod
    def setUpClass(cls):
        cls.a, cls.b = S.SyntheticRun(drawing_date=PINNED_DATE).start(), S.SyntheticRun(drawing_date=PINNED_DATE).start()
        cls.addClassCleanup(cls.a.cleanup)
        cls.addClassCleanup(cls.b.cleanup)
        cls.fa, cls.fb = files_of(cls.a.project), files_of(cls.b.project)

    def test_both_runs_completed(self):
        for proj in (self.a, self.b):
            self.assertEqual(proj.run_result[0], 0)
            self.assertEqual(proj.run_result[1]["data"]["run"]["summary"]["by_status"], {"ok": 16})

    def test_every_file_is_byte_identical(self):
        self.assertEqual(sorted(self.fa), sorted(self.fb))
        self.assertGreater(len(self.fa), 40)
        self.assertEqual([rel for rel in self.fa if self.fa[rel].read_bytes() != self.fb[rel].read_bytes()], [])

    def test_the_files_that_used_to_differ_are_in_the_comparison_and_identical(self):
        for rel in (r for r in self.fa if r.endswith(".dxf") or r.endswith("input_for_sld.xlsx")):
            self.assertEqual(self.fa[rel].read_bytes(), self.fb[rel].read_bytes(), rel)
        self.assertEqual(len([r for r in self.fa if r.endswith(".dxf")]), 4)             # two in the run folder, two copied into deliverables/TR-001/
        for rel in EMBED_DXF_HASH:
            self.assertEqual(self.fa[rel].read_bytes(), self.fb[rel].read_bytes(), rel)
        self.assertEqual(self.a.ssot("stage_14_drawings.json"), self.b.ssot("stage_14_drawings.json"))

    def test_the_hashes_in_the_manifests_are_the_hashes_of_the_files(self):
        out = self.a.ssot("stage_14_drawings.json")["outputs"]
        dxf = [entry for entry in out["files"] if entry["path"].endswith(".dxf")]
        self.assertEqual(len(dxf), 2)
        for entry in dxf:
            self.assertEqual(entry["sha256"], S.sha256_file(self.a.project / ".epc" / "runs" / S.RUN_ID / out["directory"] / entry["path"]))

    def test_the_pinned_date_is_in_the_drawings(self):
        for rel in (r for r in self.fa if r.endswith(".dxf")):
            text = self.fa[rel].read_text(encoding="utf-8", errors="replace")
            self.assertIn("2461104.0", text, rel)                                       # the Julian date of 2026-03-04, as creation and update time
            self.assertIn("04/03/2026", text, rel)                                      # the issue date of the title block
        request = json.loads(next(p for r, p in self.fa.items() if r.endswith("titleblock-request.json")).read_text(encoding="utf-8"))
        self.assertEqual(request["common"]["proy_fecha"], "04/03/2026")

    def test_the_event_logs_are_the_same_hash_chain(self):
        logs = [EventLog.for_project(p.project, S.clock) for p in (self.a, self.b)]
        self.assertEqual(logs[0].read(), logs[1].read())
        self.assertEqual(logs[0].last(), logs[1].last())

    def test_another_drawing_date_changes_the_drawings_and_nothing_else_in_the_calculation(self):
        other = S.SyntheticRun(drawing_date="2026-03-05").start()
        self.addCleanup(other.cleanup)
        fo = files_of(other.project)
        differs = {rel for rel in self.fa if self.fa[rel].read_bytes() != fo[rel].read_bytes()}
        self.assertTrue(any(rel.endswith(".dxf") for rel in differs))
        for rel in (".epc/ssot/stage_08_feeder_sizing.json", ".epc/ssot/stage_09_voltage_drop.json", ".epc/ssot/stage_15_documents.json"):
            self.assertIn(rel, self.fa)
            self.assertNotIn(rel, differs)


if __name__ == "__main__":
    unittest.main()
