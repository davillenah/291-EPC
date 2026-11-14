"""MIG-40: stage 3 runs `epc_lighting` (optional slice 17) when the `lighting` inputs are given, and is unchanged when they are not."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import epc_lighting as EL  # noqa: E402
import test_pipeline_wiring as W  # noqa: E402
from disciplines.electrical_lv.pipeline import STAGES, run  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DOC = json.loads((ROOT / "src/engines/calculation/lighting/examples/classroom.json").read_text(encoding="utf-8"))
SMALL = {"schema_version": "1.0", "luminaires": [{"id": "L1", "lamps": 2, "lamp_flux_lm": 2400}],
         "rooms": [{"id": "R1", "width_m": 4, "length_m": 6, "height_m": 2.6, "activity": "education.classroom", "luminaire": "L1",
                    "coefficient_of_utilisation": 0.97}]}


def ctx_with(section=None):
    """A context that has run stages 1-2 (the preconditions of stage 3), with the given `lighting` section."""
    inputs = W.inputs_doc()
    if section is not None:
        inputs["lighting"] = section
    ctx = W.context(engine_inputs=inputs)
    run(ctx, stop_after=2, run_id="r3")
    return ctx


class LightingSliceTests(unittest.TestCase):
    def test_without_the_section_stage_3_is_what_it_was(self):
        res = STAGES[2].run(ctx_with())
        self.assertEqual(res.status, "ok")
        self.assertEqual(set(res.outputs), {"load_schedule", "demand"})
        self.assertEqual({c["function"] for c in res.engine_calls if c["engine"] == "calculation/lighting"}, set())

    def test_with_the_section_it_adds_the_lighting_section(self):
        res = STAGES[2].run(ctx_with({"document": SMALL}))
        self.assertEqual(res.status, "ok")
        self.assertEqual(set(res.outputs), {"load_schedule", "demand", "lighting"})
        self.assertEqual(res.outputs["lighting"], EL.run(copy.deepcopy(SMALL)).as_dict())
        self.assertIn({"engine": "calculation/lighting", "function": "epc_lighting.run", "version": EL.__version__}, res.engine_calls)
        self.assertEqual(res.outputs["lighting"]["rooms"][0]["verification"]["complies"], True)
        json.dumps(res.to_dict())

    def test_findings_are_notes_for_warnings_and_major_for_a_target_not_reached(self):
        res = STAGES[2].run(ctx_with({"document": DOC}))
        mine = [f for f in res.findings if f["document"] == "lighting"]
        direct = EL.run(copy.deepcopy(DOC)).as_dict()
        self.assertEqual(sum(f["severity"] == "note" for f in mine), len(direct["warnings"]))
        failed = [i["id"] for i in direct["rooms"] + direct["areas"] if i["verification"]["complies"] is False]
        self.assertEqual([f["field"].split("/")[0] for f in mine if f["severity"] == "major"], failed)
        self.assertEqual(len({f["id"] for f in res.findings}), len(res.findings))

    def test_options_are_passed_to_the_engine(self):
        res = STAGES[2].run(ctx_with({"document": SMALL, "options": {"compute_points": False}}))
        self.assertEqual(res.outputs["lighting"], EL.run(copy.deepcopy(SMALL), EL.Options(compute_points=False)).as_dict())

    def test_a_wrong_section_blocks_with_the_reason(self):
        bad_room = copy.deepcopy(SMALL)
        bad_room["rooms"][0]["width_m"] = -1
        for section, text in (("rooms", "must be an object"), ({"document": SMALL, "colour": "red"}, "unknown input"),
                              ({"document": SMALL, "options": {"nope": 1}}, "lighting:"), ({"document": SMALL, "options": []}, "options"),
                              ({"document": bad_room}, "lighting:")):
            with self.subTest(section=section):
                res = STAGES[2].run(ctx_with(section))
                self.assertEqual(res.status, "blocked")
                self.assertIn(text, res.message)
                self.assertTrue(res.message.startswith("lighting: "))
                self.assertEqual(res.findings[0]["severity"], "blocking")

    def test_calc_check_does_not_see_the_extra_slice(self):
        from disciplines.electrical_lv.stages.calc_check_stage import logical_results
        res = STAGES[2].run(ctx_with({"document": SMALL}))
        logical = logical_results([dict(res.to_dict(), stage=3)])
        self.assertEqual([r["stage"] for r in logical], [4, 5])
        self.assertTrue(all(f["document"] != "lighting" for r in logical for f in r["findings"]))


if __name__ == "__main__":
    unittest.main()
