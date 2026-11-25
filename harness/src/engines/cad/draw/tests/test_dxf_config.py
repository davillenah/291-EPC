"""The editable folder of the DXF look (`harness/config/dxf`): typeface, text height, layers, and a tray with its text as one block."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import ezdxf   # noqa: E402
from epc_draw.core import settings, textstyle   # noqa: E402
from epc_draw.plan import core, dxfout   # noqa: E402

TRAYS = {"schema_version": "1.0", "plan": {"id": "T", "level": "L0", "scale": {"p1": [0, 0], "p2": [100, 0], "distance_m": 10}, "origin": [0, 0]}, "discipline": "electrica_BT",
         "nodes": [{"id": "a", "kind": "LU", "x": 10, "y": 10}, {"id": "b", "kind": "LU", "x": 60, "y": 10}], "lines": [{"id": "l1", "kind": "BN", "points": [[10, 10], [60, 10]]}]}


class Env:
    """The DXF settings with `folder` as the editable folder, handed in as data (no process environment)."""
    def __init__(self, folder):
        self.use = settings.use(settings.DxfSettings(config_dir=folder))

    def __enter__(self):
        self.use.__enter__()

    def __exit__(self, *a):
        self.use.__exit__(*a)


def write(folder):
    path = Path(folder) / "t.dxf"
    dxfout.write_dxf(core.process(TRAYS), path)
    return ezdxf.readfile(path)


class TestDxfConfig(unittest.TestCase):
    def test_the_shipped_folder_is_valid_and_has_the_files(self):
        folder = textstyle.REPO_CONFIG
        self.assertTrue((folder / "text.json").is_file() and (folder / "layers.json").is_file())
        self.assertEqual(textstyle.validate(json.loads((folder / "text.json").read_text())), {})

    def test_a_tray_and_its_text_are_one_block(self):
        with tempfile.TemporaryDirectory() as t, Env(""):
            dxf = write(t)
            msp = dxf.modelspace()
            self.assertEqual([e.dxftype() for e in msp].count("LWPOLYLINE"), 0)
            tray = [e for e in msp.query("INSERT") if e.dxf.name.startswith("TRAY_")]
            self.assertEqual(len(tray), 1)
            inside = {e.dxftype() for e in dxf.blocks[tray[0].dxf.name]}
            self.assertEqual(inside, {"LWPOLYLINE", "TEXT"})
            self.assertTrue(all(e.dxf.layer != "0" for e in dxf.blocks[tray[0].dxf.name]))

    def test_trays_can_be_loose_again(self):
        with tempfile.TemporaryDirectory() as t, Env(t):
            (Path(t) / "text.json").write_text(json.dumps({"trays": {"as_block": False}}))
            msp = write(t).modelspace()
            self.assertEqual([e.dxftype() for e in msp].count("LWPOLYLINE"), 1)

    def test_the_font_and_the_height_come_from_the_folder(self):
        with tempfile.TemporaryDirectory() as t, Env(t):
            (Path(t) / "text.json").write_text(json.dumps({"font": {"style": "MIFUENTE", "regular": "calibri.ttf"}, "heights": {"plan_text_m": 0.5}}))
            dxf = write(t)
            self.assertEqual(dxf.styles.get("MIFUENTE").dxf.font, "calibri.ttf")
            texts = [e for blk in dxf.blocks if blk.name.startswith("TRAY_") for e in blk.query("TEXT")]
            self.assertEqual(texts[0].dxf.style, "MIFUENTE")
            self.assertAlmostEqual(texts[0].dxf.height, 0.5)

    def test_the_layer_names_come_from_the_folder(self):
        from epc_draw.core import layers
        with tempfile.TemporaryDirectory() as t, Env(t):
            (Path(t) / "layers.json").write_text(json.dumps({"layers": {"plan.ELEC-BANDEJA": {"name": "MI-BANDEJA"}}}))
            dxf = write(t)
            self.assertIn("MI-BANDEJA", {l.dxf.name for l in dxf.layers})
            self.assertEqual(layers.name("plan.ELEC-BANDEJA"), "MI-BANDEJA")
            tray = [e for e in dxf.modelspace().query("INSERT") if e.dxf.name.startswith("TRAY_")][0]
            self.assertEqual(tray.dxf.layer, "MI-BANDEJA")

    def test_without_the_folder_the_defaults_are_the_old_values(self):
        with Env(""):
            look = textstyle.load()
        self.assertEqual(look["font"]["regular"], "arial.ttf")
        self.assertEqual((look["heights"]["titleblock_mm"], look["heights"]["legal_notice_mm"], look["heights"]["plan_text_m"]), (1.7, 1.0, 0.15))

    def test_the_final_step_keeps_the_layers_and_follows_the_typeface_of_the_folder(self):
        from epc_draw.core import style_unify
        with tempfile.TemporaryDirectory() as t, Env(t):
            (Path(t) / "text.json").write_text(json.dumps({"font": {"regular": "calibri.ttf"}}))
            self.assertEqual(style_unify.new_layer_name("291-E-CABL-TRAY-N"), "291-E-CABL-TRAY-N")          # the layers already carry their final names
            path = Path(t) / "t.dxf"
            dxfout.write_dxf(core.process(TRAYS), path)
            self.assertEqual(style_unify.unify(path), {})
            self.assertEqual(ezdxf.readfile(path).styles.get("ARIAL").dxf.font, "calibri.ttf")

    def test_a_bad_value_is_reported(self):
        self.assertIn("heights.plan_text_m", textstyle.validate({"font": {"regular": "a", "bold": "b", "style": "c", "style_bold": "d"}, "heights": {"plan_text_m": -1, "titleblock_mm": 1, "legal_notice_mm": 1, "diagram_text_mm": 1, "frame_text_mm": 1}, "trays": {"as_block": True, "kinds": [], "block_prefix": "T"}}))


if __name__ == "__main__":
    unittest.main()
