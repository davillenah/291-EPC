"""OPT-01: the pipeline times every stage it runs and keeps the seconds in the context, apart from every result."""
import json
import unittest
from types import SimpleNamespace

from disciplines.electrical_lv import pipeline
from disciplines.electrical_lv.stages.base import PipelineContext, StageResult


def stub(number):
    return SimpleNamespace(number=number, spec=SimpleNamespace(number=number, slug=f"s{number}"),
                           run=lambda context, n=number: StageResult(stage=n, status="ok"))


class StageTimings(unittest.TestCase):
    def test_every_stage_run_is_timed(self):
        context = PipelineContext()
        pipeline.run(context, stages=[stub(1), stub(2), stub(3)], stop_after=2)
        self.assertEqual(sorted(context.timings), [1, 2])
        self.assertTrue(all(isinstance(v, float) and v >= 0 for v in context.timings.values()))

    def test_timings_start_empty_on_each_run(self):
        context = PipelineContext()
        pipeline.run(context, stages=[stub(1), stub(2)])
        pipeline.run(context, stages=[stub(1)])
        self.assertEqual(sorted(context.timings), [1])

    def test_timings_are_not_in_the_results(self):
        context = PipelineContext()
        res = pipeline.run(context, stages=[stub(1)])
        self.assertNotIn("seconds", str(res.to_dict()))

    def test_the_file_has_the_seconds_of_each_stage(self):
        written = {}
        store = SimpleNamespace(write_run_file=lambda token, run_id, name, data: written.update({name: data}))
        recorder = SimpleNamespace(run_id="r1", token="t", store=store)
        context = PipelineContext()
        context.timings = {1: 0.5, 2: 1.25}
        pipeline._write_timings(context, recorder, [stub(1), stub(2)])
        doc = json.loads(written["stage_timings.json"])
        self.assertEqual(doc["total_seconds"], 1.75)
        self.assertEqual([r["slug"] for r in doc["stages"]], ["s1", "s2"])


if __name__ == "__main__":
    unittest.main()
