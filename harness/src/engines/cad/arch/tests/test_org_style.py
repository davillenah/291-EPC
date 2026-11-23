"""What an organization changes of the way the engine draws: the width of each pen, the pen of each layer, the height of each text, and its own sheet (margins, pens, title block)."""
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import ezdxf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE.parent.parent / "titleblock" / "src"))
sys.path.insert(0, str(HERE))

from epc_arch import Options, recognize                          # noqa: E402
from epc_arch.drawing import build_drawing, load_style, style_errors, style_with   # noqa: E402
from epc_arch.export.export_dxf import to_dxf                     # noqa: E402
from epc_arch.export.export_svg import to_svg                     # noqa: E402
from epc_arch import cli_v2                                       # noqa: E402
iram_template = cli_v2.iram_template
import helpers                                                    # noqa: E402


class TestOrgStyle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.arch = recognize(helpers.room_dxf(), "flat.dxf", Options()).architecture

    def test_a_pen_a_layer_and_a_text_style_can_be_changed(self):
        style = style_with({"pens": {"pen_050": 0.7}, "layer_pens": {"291-A-DOOR-N": "pen_050"}, "text_styles": {"TXT_25": 3.0}})
        self.assertEqual(style.pens["pen_050"], 0.7)
        self.assertEqual(style.layers["291-A-WALL-FULL-N"].width, 0.7)
        self.assertEqual(style.layers["291-A-DOOR-N"].width, 0.7)
        self.assertEqual(style.text_styles["TXT_25"], 3.0)
        standard = load_style()
        self.assertEqual(standard.pens["pen_050"], 0.5)                                # the standard one is not touched
        self.assertIs(style_with(None), standard)

    def test_the_drawing_comes_out_with_the_organizations_widths_and_heights(self):
        style = style_with({"pens": {"pen_050": 0.8}, "text_styles": {"TXT_25": 3.5}})
        svg = to_svg(build_drawing(self.arch, sheet="A3", style=style), style)
        standard = to_svg(build_drawing(self.arch, sheet="A3"))
        self.assertIn('stroke-width="0.8"', svg)
        self.assertNotIn('stroke-width="0.8"', standard)
        self.assertNotEqual(svg, standard)
        doc = ezdxf.read(io.StringIO(to_dxf(build_drawing(self.arch, sheet="A3", style=style), style)))
        self.assertTrue(any(e.dxf.lineweight == 80 for e in doc.layers))                # the wall cut at 0,8 mm

    def test_what_is_not_valid_is_said_field_by_field(self):
        errors = style_errors({"pens": {"pen_050": 9, "pen_99": 1}, "text_styles": {"TXT_25": "big"}, "layer_pens": {"A-NOPE": "pen_050", "291-A-DOOR-N": "pen_7"}, "colour": "red"})
        for key in ("pens.pen_050", "pens.pen_99", "text_styles.TXT_25", "layer_pens.A-NOPE", "layer_pens.291-A-DOOR-N", "colour"):
            self.assertIn(key, errors)
        with self.assertRaises(ValueError):
            style_with({"pens": {"pen_050": 9}})

    def test_the_sheet_of_the_organization_is_the_one_the_plan_is_drawn_on(self):
        config = {"frame": {"margin_left": 30, "margin": 12, "strip": 6}, "pens": {"frame": 1.4}}
        mine, standard = iram_template("A1", config), iram_template("A1")
        if mine is None or standard is None:
            self.skipTest("epc_titleblock is not here")
        self.assertNotEqual(mine.free, standard.free)
        self.assertEqual(iram_template("A1", config).free, mine.free)                 # the same change gives the same sheet

    def test_the_command_line_takes_both(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            (t / "plan.dxf").write_bytes(helpers.room_dxf())
            (t / "style.json").write_text(json.dumps({"pens": {"pen_050": 0.9}}), encoding="utf-8")
            (t / "sheet.json").write_text(json.dumps({"pens": {"frame": 1.5}}), encoding="utf-8")
            env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(HERE.parent / "src"), str(HERE.parent.parent / "titleblock" / "src")])}
            res = subprocess.run([sys.executable, "-m", "epc_arch.cli_v2", str(t / "plan.dxf"), "--out", str(t / "o"), "--formats", "svg", "--style", str(t / "style.json"),
                                  "--sheet-config", str(t / "sheet.json")], capture_output=True, text=True, env=env)
            self.assertEqual(res.returncode, 0, res.stderr[-400:])
            svg = next((t / "o").glob("*.svg")).read_text(encoding="utf-8")
            self.assertIn('stroke-width="0.9"', svg)
            bad = subprocess.run([sys.executable, "-m", "epc_arch.cli_v2", str(t / "plan.dxf"), "--out", str(t / "o2"), "--style", str(t / "nada.json")], capture_output=True, text=True, env=env)
            self.assertEqual(bad.returncode, 1)


if __name__ == "__main__":
    unittest.main()
