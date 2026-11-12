"""D18 in the discipline: a grouping outside the tables or a buried D2 circuit without its installation data blocks the stages with the engine's message."""
import unittest

import test_pipeline_wiring as W
from disciplines.electrical_lv.pipeline import STAGES
from disciplines.electrical_lv.stages.base import StageResult


class D18BlockedTests(unittest.TestCase):
    def ready(self):
        ctx = W.context()
        ctx.design_basis = {"supply": {}}
        ctx.results = {3: StageResult(3, "ok")}
        return ctx

    def assert_blocked(self, ctx, text, stages=W.CHAIN_STAGES):
        for number in stages:
            res = STAGES[number - 1].run(ctx)
            with self.subTest(stage=number):
                self.assertEqual(res.status, "blocked")
                self.assertEqual((res.outputs, res.engine_calls), ({}, []))
                self.assertIn(text, res.message)
                self.assertTrue(res.findings)

    def test_grouping_outside_the_table_blocks_with_the_engine_message(self):
        ctx = self.ready()
        ctx.engine_inputs["circuits"]["L-01"]["grouped"] = 10          # Table 771.16.IV has 9 and 12, not 10
        self.assert_blocked(ctx, "Tabla 771.16.IV")
        self.assert_blocked(ctx, "AGRUP_CIRCUITOS", stages=(4,))

    def test_a_tabulated_grouping_does_not_block(self):
        ctx = self.ready()
        ctx.engine_inputs["circuits"]["L-01"]["grouped"] = 12
        self.assertEqual(STAGES[3].run(ctx).status, "ok")

    def test_buried_d2_without_column_blocks_and_asks_for_it(self):
        ctx = self.ready()
        ctx.engine_inputs["circuits"]["L-01"]["method"] = "D2"
        self.assert_blocked(ctx, "COLUMNA_D2")

    def test_buried_d2_with_its_column_calculates(self):
        ctx = self.ready()
        ctx.engine_inputs["circuits"]["L-01"].update({"method": "D2", "d2_column": "c2_2x"})
        self.assertEqual(STAGES[3].run(ctx).status, "ok")

    def test_grouped_d2_blocks_without_separation_and_passes_with_it(self):
        ctx = self.ready()
        ctx.engine_inputs["circuits"]["L-01"].update({"method": "D2", "d2_column": "c2_2x", "grouped": 2})
        self.assert_blocked(ctx, "SEPARACION_CABLES", stages=(4,))
        ctx = self.ready()
        ctx.engine_inputs["circuits"]["L-01"].update({"method": "D2", "d2_column": "c2_2x", "grouped": 2, "spacing": "0,25 m"})
        self.assertEqual(STAGES[3].run(ctx).status, "ok")


if __name__ == "__main__":
    unittest.main()
