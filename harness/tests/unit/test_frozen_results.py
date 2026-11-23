"""COD-22 / COD-12: what a stage hands on cannot be reassigned. The context stays mutable on purpose: it is what the stages fill in order."""
import dataclasses
import unittest

from disciplines.electrical_lv.pipeline import RunResult
from disciplines.electrical_lv.stages.base import StageResult


class FrozenResults(unittest.TestCase):
    def test_stage_result_is_frozen(self):
        result = StageResult(stage=1, status="ok") if "ok" in __import__("disciplines.electrical_lv.stages.base", fromlist=["STATUSES"]).STATUSES else None
        self.assertIsNotNone(result)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.status = "failed"
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.outputs = {}

    def test_run_result_is_frozen(self):
        run = RunResult("r1")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            run.summary = {}


if __name__ == "__main__":
    unittest.main()
