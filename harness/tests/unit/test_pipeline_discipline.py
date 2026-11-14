"""electrical_lv pipeline: the 12-stage table against the PRD, ordering, not_available rules, stages 1-3 (synthetic data)."""
import json
import re
import tempfile
import unittest
from pathlib import Path

from disciplines.electrical_lv import pipeline
from disciplines.electrical_lv.pipeline import STAGE_TABLE, STAGES, PipelineContext, run
from disciplines.electrical_lv.rules.design_rules import check_preconditions, load_preconditions
from disciplines.electrical_lv.stages import EngineStage
from disciplines.electrical_lv.stages.base import Stage, StageResult
from disciplines.electrical_lv.stages.table import WIRED_STAGES

PRD = Path(__file__).resolve().parents[2] / "docs" / "prsad" / "PRD.md"
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


def prd_rows():
    text = PRD.read_text(encoding="utf-8")
    section = text.split("## 12.")[1].split("\n## 13.")[0]
    rows = []
    for line in section.splitlines():
        cells = [c.strip().replace("`", "") for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[0].isdigit():
            rows.append(cells)
    return rows


class Inputs:
    """A temp inputs folder with one plan and a load-list file."""

    def __init__(self, test, loads=LOADS):
        tmp = tempfile.TemporaryDirectory()
        test.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "inputs" / "plans").mkdir(parents=True)
        (root / "inputs" / "plans" / "a1.dxf").write_text("plan", encoding="utf-8")
        self.loads_path = root / "loads.json"
        self.loads_path.write_text(json.dumps(loads), encoding="utf-8")
        self.inputs_dir = str(root / "inputs")

    def context(self):
        return PipelineContext(answers=ANSWERS, inputs_dir=self.inputs_dir, load_list_path=str(self.loads_path))


class TableTests(unittest.TestCase):
    def test_table_matches_the_prd(self):
        rows = prd_rows()
        self.assertEqual(len(rows), 12)
        self.assertEqual(len(STAGE_TABLE), 12)
        for spec, (number, title, engines, status) in zip(STAGE_TABLE, rows):
            with self.subTest(stage=spec.number):
                self.assertEqual(spec.number, int(number))
                self.assertEqual(spec.title, title)
                self.assertEqual(spec.engines_text, engines)
                self.assertEqual(spec.status_text, status)
                self.assertIn(spec.phase1_status, ("implemented", "in development", "planned"))
                self.assertTrue(status.startswith(spec.phase1_status) or status == "in part")
                for group, _name in spec.engines:
                    self.assertIn(group, engines)

    def test_order_is_fixed_and_slugs_are_unique(self):
        self.assertEqual([s.number for s in STAGES], list(range(1, 13)))
        slugs = [s.spec.slug for s in STAGES]
        self.assertEqual(len(set(slugs)), 12)
        self.assertTrue(all(re.fullmatch(r"[a-z_]+", s) for s in slugs))

    def test_wiring_flags(self):
        wired = [s.number for s in STAGES if s.wired]
        self.assertEqual(wired, list(WIRED_STAGES))
        self.assertEqual(wired, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
        to_wire = [s.number for s in STAGES if s.wiring_task == "MIG-30c"]
        self.assertEqual(to_wire, [5, 7, 8, 10, 11])         # 3 and 6 are grouped stages: their slices carry the wiring
        self.assertEqual(STAGES[8].wiring_task, "MIG-35a")
        self.assertEqual(STAGES[11].wiring_task, "MIG-32")
        self.assertEqual(STAGES[3].wiring_task, "MIG-39a")


class NotAvailableTests(unittest.TestCase):
    def test_unwired_stages_return_no_outputs_and_their_message(self):
        res = run(PipelineContext(), run_id="r")  # nothing given: stage 1 blocks, so use stages directly
        self.assertEqual(res.results[0].status, "blocked")
        ctx = PipelineContext(pipeline_run_id="r")
        unwired = [s for s in STAGES if not s.wired]
        self.assertEqual([s.number for s in unwired], [])
        # stage 4 is wired (MIG-39a): its not_available result without the `transformer` inputs is tested in test_supply_stage.py
        for stage in unwired:
            with self.subTest(stage=stage.number):
                out = stage.run(ctx)
                self.assertEqual(out.status, "not_available")
                self.assertEqual(out.outputs, {})
                self.assertEqual(out.engine_calls, [])
                self.assertEqual(out.findings, [])
        messages = {s.number: s.run(ctx).message for s in unwired}
        self.assertEqual(EngineStage(STAGE_TABLE[4]).run(ctx).message, "engine wiring: MIG-30c")
        self.assertNotIn(9, messages)
        self.assertNotIn(12, messages)

    def test_planned_stages_never_return_outputs(self):
        for stage in STAGES:
            if stage.spec.phase1_status == "planned" and not stage.wired:
                self.assertEqual(stage.run(PipelineContext()).outputs, {})

    def test_a_not_available_result_cannot_carry_outputs(self):
        with self.assertRaises(ValueError):
            StageResult(4, "not_available", outputs={"x": 1})
        with self.assertRaises(ValueError):
            StageResult(4, "weird")


class EarlyStageTests(unittest.TestCase):
    def test_stages_1_to_2_run_on_synthetic_inputs(self):
        ctx = Inputs(self).context()
        res = run(ctx, stop_after=2, run_id="r1")
        self.assertEqual([r.status for r in res.results], ["ok", "ok"])
        self.assertEqual(res.results[0].outputs["profile"]["project_code"], "TEST-001")
        self.assertEqual(ctx.inputs_manifest["files"][0]["path"], "plans/a1.dxf")
        self.assertEqual(res.results[1].outputs["requirements"]["design_basis"]["supply"]["earthing_system"], "TN")
        self.assertTrue(res.results[1].outputs["input_verification"]["verified"])
        self.assertTrue(res.summary["ok"])
        self.assertEqual(res.summary["stopped_at"], None)

    def test_a_run_stops_at_stage_3_when_the_calculation_data_is_missing(self):
        # these answers have no supply voltage and the loads have no run length: the engines are not called
        res = run(Inputs(self).context(), run_id="r1")
        self.assertEqual([r.status for r in res.results], ["ok", "ok", "blocked"])
        self.assertEqual(res.summary["stopped_at"], 3)
        self.assertEqual(res.results[2].outputs, {})
        self.assertIn("supply.voltage", res.results[2].message)
        self.assertFalse(res.summary["ok"])

    def test_missing_earthing_blocks_stage_1(self):
        ctx = Inputs(self).context()
        ctx.answers = {**ANSWERS, "supply": {}}
        res = run(ctx, run_id="r1")
        self.assertEqual([r.status for r in res.results], ["blocked"])
        self.assertIn("D24", res.results[0].message)
        self.assertEqual(res.summary["stopped_at"], 1)

    def test_verification_findings_block_stage_2_and_stop_the_run(self):
        bad = json.loads(json.dumps(LOADS))
        bad["loads"][0]["area"] = "ZZ"
        res = run(Inputs(self, bad).context(), run_id="r1")
        self.assertEqual([r.status for r in res.results], ["ok", "blocked"])
        self.assertTrue(res.results[1].findings[0]["clause"].endswith("IV-02"))
        self.assertEqual(res.summary["stopped_at"], 2)

    def test_stop_after_ends_the_run_after_that_stage(self):
        res = run(Inputs(self).context(), stop_after=2, run_id="r")
        self.assertEqual(res.summary["stop_after"], 2)
        self.assertEqual(len(res.results), 2)


class RunBehaviourTests(unittest.TestCase):
    class Boom(Stage):
        wired = True

        def execute(self, context):
            raise RuntimeError("boom")

    class Fine(Stage):
        wired = True

        def execute(self, context):
            return self.result("ok", outputs={"n": self.number})

    def test_run_stops_at_the_first_failed_stage(self):
        stages = [self.Fine(STAGE_TABLE[8]), self.Boom(STAGE_TABLE[11]), self.Fine(STAGE_TABLE[8])]
        res = run(PipelineContext(), stages=stages, run_id="r")
        self.assertEqual([r.status for r in res.results], ["ok", "failed"])
        self.assertEqual(res.summary["stopped_at"], 12)
        self.assertFalse(res.summary["ok"])
        self.assertIn("RuntimeError: boom", res.results[1].message)

    def test_run_can_go_on_when_told_to(self):
        stages = [self.Boom(STAGE_TABLE[8]), self.Fine(STAGE_TABLE[11])]
        res = run(PipelineContext(), stages=stages, run_id="r", stop_on=())
        self.assertEqual([r.status for r in res.results], ["failed", "ok"])

    def test_stop_after_must_be_a_stage_number(self):
        with self.assertRaises(ValueError):
            run(PipelineContext(), stop_after=13)

    def test_same_inputs_and_run_id_give_the_same_result(self):
        inputs = Inputs(self)
        first = run(inputs.context(), run_id="fixed", clock=lambda: "2026-01-01T00:00:00Z").to_dict()
        second = run(inputs.context(), run_id="fixed", clock=lambda: "2026-01-01T00:00:00Z").to_dict()
        self.assertEqual(first, second)
        self.assertEqual(first["started_at"], "2026-01-01T00:00:00Z")
        self.assertEqual(json.loads(json.dumps(first)), first)

    def test_without_clock_there_are_no_timestamps_and_the_run_id_is_generated(self):
        res = run(Inputs(self).context(), stop_after=1)
        self.assertIsNone(res.started_at)
        self.assertEqual(len(res.pipeline_run_id), 36)

    def test_finding_ids_are_unique_across_the_run(self):
        bad = json.loads(json.dumps(LOADS))
        bad["loads"][0]["area"] = "ZZ"
        bad["loads"].append(dict(bad["loads"][0]))
        res = run(Inputs(self, bad).context(), run_id="r")
        ids = [f["id"] for r in res.results for f in r.findings]
        self.assertGreater(len(ids), 1)
        self.assertEqual(len(ids), len(set(ids)))


class RulesTests(unittest.TestCase):
    def test_every_stage_has_an_entry_and_stage_3_needs_loads_and_stage_2(self):
        table = load_preconditions()
        self.assertEqual(sorted(table), list(range(1, 13)))
        findings = check_preconditions(3, PipelineContext(loads={"loads": []}), "r", table)
        self.assertEqual([f["clause"].split()[-1] for f in findings], ["PC-03-1", "PC-03-2"])
        ctx = PipelineContext(loads=LOADS, results={2: StageResult(2, "ok")})
        self.assertEqual(check_preconditions(3, ctx), [])

    def test_unmet_precondition_blocks_a_wired_stage(self):
        res = STAGES[1].run(PipelineContext())
        self.assertEqual(res.status, "blocked")
        self.assertEqual(res.reason, "precondition")
        self.assertEqual(res.outputs, {})

    def test_module_exports(self):
        self.assertIs(pipeline.STAGES, STAGES)


if __name__ == "__main__":
    unittest.main()
