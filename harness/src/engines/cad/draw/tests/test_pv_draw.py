"""OPT-02 (ADR-0040): `epc_drawing.draw_pv(PvDrawInput, ...)` calls the same writers, in the same order, with the same data."""
import unittest
from pathlib import Path
from unittest import mock

from epc_draw.pv import details as pv_details, diagrams as pv_diagrams, roof as pv_roof
from epc_draw.pv.draw import PvDrawInput, draw_pv


class TestDrawPv(unittest.TestCase):
    def run_draw(self, **given):
        entrada = PvDrawInput(result={"r": 1}, language="es", stamp_date="2026-03-04", **given)
        with mock.patch.object(pv_diagrams, "write_all", return_value={"g": Path("g.dxf")}) as ground, mock.patch.object(pv_roof, "write_all", return_value={"r": Path("r.dxf")}) as roof, \
                mock.patch.object(pv_details, "write", return_value=Path("d.dxf")) as detail:
            out = draw_pv(entrada, "out", "P")
        return out, ground, roof, detail

    def test_ground_layout_then_its_detail(self):
        (drafts, ran), ground, roof, detail = self.run_draw(layout={"l": 1}, parts={"module": {}})
        self.assertEqual(ran, ["pv_diagrams.write_all", "pv_details.write"])
        self.assertEqual(list(drafts), ["g", "P_pv_equipment_detail"])
        ground.assert_called_once_with({"l": 1}, {"r": 1}, Path("out/pv_drafts"), "P_pv", "es", "2026-03-04")
        roof.assert_not_called()

    def test_roof_planes_carry_the_detail_only_without_a_ground_layout(self):
        (drafts, ran), _, roof, detail = self.run_draw(roof={"p": 1}, parts={"module": {}})
        self.assertEqual(ran, ["pv_roof.write_all", "pv_details.write"])
        both, _, _, _ = self.run_draw(layout={"l": 1}, roof={"p": 1}, parts={})
        self.assertEqual(both[1], ["pv_diagrams.write_all", "pv_details.write", "pv_roof.write_all"])

    def test_no_detail_when_the_writer_finds_no_record(self):
        entrada = PvDrawInput(result={}, roof={"p": 1}, parts={})
        with mock.patch.object(pv_roof, "write_all", return_value={}), mock.patch.object(pv_details, "write", return_value=None):
            self.assertEqual(draw_pv(entrada, "out", "P"), ({}, ["pv_roof.write_all"]))

    def test_the_input_is_frozen_and_checked(self):
        with self.assertRaises(Exception):
            PvDrawInput(result={}).language = "es"
        with self.assertRaises(TypeError):
            draw_pv({"result": {}}, "out", "P")


if __name__ == "__main__":
    unittest.main()
