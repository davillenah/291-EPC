"""MIG-3Z: stage 14 reads the optional `engine_inputs["drawings"]["date"]` (ISO date), validates it and passes it to the drawing engine; absent means not pinned."""
import types
import unittest
from unittest import mock

from disciplines.electrical_lv.stages import output_stages as OS
from disciplines.electrical_lv.stages.base import StageInputError


def context(engine_inputs):
    return types.SimpleNamespace(engine_inputs=engine_inputs)


class TestDrawingDate(unittest.TestCase):
    def test_absent_is_not_pinned(self):
        for given in (None, {}, {"drawings": {}}, {"drawings": {"date": None}}, {"drawings": "x"}, {"boq": {"allowance_pct": 5}}):
            with self.subTest(given=given):
                self.assertIsNone(OS.drawing_date(context(given)))

    def test_an_iso_date_is_passed_as_it_is(self):
        self.assertEqual(OS.drawing_date(context({"drawings": {"date": "2026-03-04"}})), "2026-03-04")

    def test_anything_else_blocks_the_stage_with_the_reason(self):
        for bad in ("04/03/2026", "2026-3-4", "2026-02-30", "2026-03-04T10:00:00", 20260304, "", "today"):
            with self.subTest(bad=bad), self.assertRaises(StageInputError) as caught:
                OS.drawing_date(context({"drawings": {"date": bad}}))
            self.assertIn("engine_inputs.drawings.date", caught.exception.errors[0])

    def test_the_stage_passes_the_date_to_the_engine_and_nothing_without_it(self):
        stage = OS.DrawingsStage(mock.Mock())
        chain = {"form": {"board": {"name": "T1"}}, "criteria": {}}
        for given, expected in (({"drawings": {"date": "2026-03-04"}}, "2026-03-04"), ({}, None)):
            with self.subTest(expected=expected), mock.patch.object(OS.EC, "chain", return_value=chain), mock.patch.object(OS.DrawingsStage, "_target", return_value="/x"), \
                    mock.patch("epc_drawing.board_design.design", return_value={"ok": False, "error": "stop"}) as design, mock.patch.object(OS.Stage, "result"):
                stage.execute(types.SimpleNamespace(engine_inputs=given))
            self.assertEqual(design.call_args.kwargs["drawing_date"], expected)

    def test_an_invalid_date_makes_the_stage_blocked_not_failed(self):
        stage = OS.DrawingsStage(mock.Mock())
        with mock.patch.object(OS.EC, "chain", return_value={"form": {"board": {"name": "T1"}}, "criteria": {}}), mock.patch.object(OS.DrawingsStage, "_target", return_value="/x"), \
                mock.patch.object(OS.Stage, "_blocked", return_value="blocked") as blocked:
            outcome = stage._guarded(types.SimpleNamespace(engine_inputs={"drawings": {"date": "soon"}}))
        self.assertEqual(outcome, "blocked")
        self.assertIn("engine_inputs.drawings.date", blocked.call_args.args[1][0])


if __name__ == "__main__":
    unittest.main()
