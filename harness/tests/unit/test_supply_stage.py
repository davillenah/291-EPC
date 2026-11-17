"""MIG-39a: stage 4 (supply and transformer sizing) calls epc_transformer_sizing when the `transformer` inputs are given."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import epc_transformer_sizing as TS  # noqa: E402
import test_pipeline_wiring as W  # noqa: E402
from disciplines.electrical_lv.pipeline import STAGES, run  # noqa: E402

GOOD = {"demand_kva": 400, "reserve_pct": 25, "secondary_v": 400}


def ctx_with(section=None):
    """A context that has run stages 1-3 (the preconditions of stage 4), with the given `transformer` section."""
    inputs = W.inputs_doc()
    if section is not None:
        inputs["transformer"] = section
    ctx = W.context(engine_inputs=inputs)
    run(ctx, stop_after=3, run_id="r6")
    return ctx


class SupplyStageTests(unittest.TestCase):
    def test_without_the_section_it_is_not_available(self):
        res = STAGES[3].run(ctx_with())
        self.assertEqual((res.status, res.reason, res.outputs, res.engine_calls, res.findings), ("not_available", "no_transformer_inputs", {}, [], []))
        self.assertEqual(res.message, "no transformer to size: no `transformer` inputs were given (the installation is taken from the low-voltage network as the supply data say)")

    def test_with_the_section_it_runs_the_engine(self):
        res = STAGES[3].run(ctx_with(GOOD))
        direct = TS.size_transformer(400, 400, 25)
        self.assertEqual(res.status, "ok")
        self.assertEqual({k: res.outputs[k] for k in direct}, direct)
        self.assertEqual(res.outputs["inputs"], GOOD)
        self.assertEqual(res.engine_calls, [{"engine": "calculation/transformer_sizing", "function": "epc_transformer_sizing.size_transformer", "version": TS.__version__}])
        self.assertEqual(len(res.findings), len(direct["assumptions"]))
        self.assertTrue(all(f["severity"] == "note" and f["status"] == "open" for f in res.findings))
        json.dumps(res.to_dict())

    def test_invalid_values_block_with_the_engine_message(self):
        cases = {"reserve_pct": ("reserve_pct is required", None), "demand_kva": ("demand_kva must be", 0), "secondary_v": ("un_v must be", -1)}
        for key, (text, bad) in cases.items():
            with self.subTest(key=key):
                res = STAGES[3].run(ctx_with({**GOOD, key: bad}))
                self.assertEqual((res.status, res.outputs, res.engine_calls), ("blocked", {}, []))
                self.assertIn(text, res.message)
                self.assertEqual(res.findings[0]["severity"], "blocking")

    def test_missing_key_negative_reserve_and_too_large(self):
        for section, text in (({"demand_kva": 400, "secondary_v": 400}, "reserve_pct is required"),
                              ({**GOOD, "reserve_pct": -5}, "reserve_pct must be"),
                              ({**GOOD, "demand_kva": 5000}, "paralleling not modelled"),
                              ({**GOOD, "colour": "red"}, "unknown input"),
                              ("400 kVA", "must be an object")):
            with self.subTest(section=section):
                res = STAGES[3].run(ctx_with(section))
                self.assertEqual(res.status, "blocked")
                self.assertIn(text, res.message)

    def test_in_the_full_pipeline(self):
        inputs = W.inputs_doc()
        inputs["transformer"] = dict(GOOD)
        done = run(W.context(engine_inputs=inputs), run_id="r")
        stage4 = done.results[3]
        self.assertEqual((stage4.stage, stage4.status), (4, "ok"))
        self.assertEqual(stage4.outputs["rating_kva"], 500)
        self.assertNotIn(4, done.summary["not_available"])
        self.assertEqual([r.status for r in done.results if r.stage == 9], ["ok"])
        self.assertFalse([f for f in done.results[8].findings if "stage 4" in str(f.get("document", "")) or f.get("document") == "supply_transformer"])


if __name__ == "__main__":
    unittest.main()


class DemandFromTheBoard(unittest.TestCase):
    """`"demand": "board"` asks the engines for the demand: head current of the board as three-phase apparent power."""

    def run4(self, section):
        import test_pipeline_wiring as W
        inputs = W.inputs_doc()
        inputs["transformer"] = section
        ctx = W.context(engine_inputs=inputs)
        run(ctx, stop_after=3, run_id="r")
        return ctx, STAGES[3].run(ctx)

    def test_the_demand_is_the_apparent_power_of_the_head_current(self):
        import epc_transformer_sizing as TS
        from epc_aea90364 import board_feeders
        ctx, res = self.run4({"demand": "board", "reserve_pct": 20, "secondary_v": 400})
        self.assertEqual(res.status, "ok", res.message)
        ch = ctx.engine_cache["chain"]
        amps, _ = board_feeders.head(ch["calc"]["datos"], ch["calc"]["detalle"], ch["criteria"])
        self.assertEqual(res.outputs["required_kva"], TS.required_apparent_power_kva(TS.apparent_power_kva(amps, ch["form"]["board"]["voltage_v"]), 20))
        self.assertTrue([f for f in res.findings if "demand of the board" in f["value"]])
        self.assertIn("epc_transformer_sizing.apparent_power_kva", [c["function"] for c in res.engine_calls])

    def test_both_a_demand_and_the_board_or_another_word_block(self):
        for section in ({"demand": "board", "demand_kva": 10, "reserve_pct": 20, "secondary_v": 400}, {"demand": "mine", "reserve_pct": 20, "secondary_v": 400}):
            _, res = self.run4(section)
            self.assertEqual(res.status, "blocked")
