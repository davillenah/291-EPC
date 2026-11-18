"""MIG-31: a run through the wired stages (engines) with a ProjectStore writes plain JSON for every stage and keeps the results.

Needs the engine packages on PYTHONPATH (the gate's `harness-tests` environment has them). Reuses the synthetic project of
test_pipeline_wiring; the store lives in a temp folder.
"""
import json
import tempfile
import unittest
from pathlib import Path

import test_pipeline_wiring as W

from disciplines.electrical_lv.intake.profile import build_profile
from disciplines.electrical_lv.intake.schema_check import load_schema, validate
from disciplines.electrical_lv.pipeline import STAGES, run
from disciplines.electrical_lv.store import ProjectStore

CLOCK = lambda: "2026-01-01T00:00:00Z"  # noqa: E731
ANSWERS = {
    "project_code": "TEST-001",
    "client": {"name": "Synthetic Client"},
    "site": {"address": "Nowhere 1", "installation_type": "test"},
    "supply": {"voltage": {"value": W.CH.BOARD["TENSION_V"], "unit": "V"}, "earthing_system": "TN",
               "short_circuit_level": {"value": W.CH.BOARD["ICC_KA"], "unit": "kA", "origin": "declared by test"}},
    "language": "en",
}


class WiredRunWithStore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.holder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.holder.cleanup)
        cls.store = ProjectStore(Path(cls.holder.name) / "proj")
        cls.store.init_from_template()
        ctx = W.context(profile=build_profile(ANSWERS), store=cls.store)
        cls.res = run(ctx, stop_after=11, run_id="r1", clock=CLOCK)
        cls.ctx = ctx

    def test_every_stage_has_its_file_and_it_equals_the_result(self):
        self.assertEqual([r.status for r in self.res.results],
                         ["ok"] * 3 + ["not_available"] + ["ok"] * 7)
        for r in self.res.results:
            name = f"stage_{r.stage:02d}_{STAGES[r.stage - 1].spec.slug}.json"
            self.assertEqual(self.store.read_ssot(name), json.loads(json.dumps(r.to_dict())), name)

    def test_the_state_lists_the_stages_and_the_engine_findings(self):
        state = self.store.read_state()
        self.assertEqual(validate(state, load_schema("master_project_state.schema.json")), [])
        self.assertEqual((state["status"], len(state["stages"])), ("paused", 11))
        engine_findings = [f for r in self.res.results for f in r.findings]
        self.assertEqual(state["open_findings"], engine_findings)
        self.assertEqual([f["id"] for f in engine_findings], [f"F-{i:04d}" for i in range(1, len(engine_findings) + 1)])

    def test_the_drawing_stage_wrote_under_the_run_folder(self):
        self.assertEqual(Path(self.ctx.work_dir), self.store.root / ".epc" / "runs" / "r1")
        directory = self.res.results[9].outputs["directory"]
        self.assertTrue(any((self.store.root / ".epc" / "runs" / "r1" / directory).glob("*")))

    def test_progress_has_one_line_per_stage(self):
        lines = self.store.read_progress().splitlines()[2:]
        self.assertEqual(len(lines), 11)
        self.assertIn("| stage 4 supply_transformer | not_available | no transformer to size", lines[3])


if __name__ == "__main__":
    unittest.main()
