"""The 3D model of a PV plant raised from its layout: faces per module, rails and posts, pads and station; refuses a layout with no tables."""
import copy
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import ezdxf

from epc_drawing import pv_model3d

PLANT = json.loads((Path(__file__).parent / "fixtures" / "pv_plant.json").read_text(encoding="utf-8"))


def geometry():
    g = copy.deepcopy(PLANT["geometry"])
    g["module"] = {"dimensions_mm": [2278.0, 1134.0], "gap_m": 0.02, "front_clearance_m": 0.5}
    g["tilts_deg"] = {a["id"]: 20.0 for a in PLANT["result"]["arrays"]}
    for t in g["tables"]:
        t.setdefault("array", PLANT["result"]["arrays"][0]["id"])
    g["tilts_deg"].setdefault(g["tables"][0]["array"], 20.0)
    return g


class TestPvModel3d(unittest.TestCase):
    def test_every_module_is_six_faces_and_the_layers_are_the_3d_ones(self):
        g = geometry()
        with tempfile.TemporaryDirectory() as tmp:
            path = pv_model3d.write(g, PLANT["result"], tmp, "PVT", stamp_date="2026-11-19")
            self.assertTrue(path.name.endswith("_pv_model_3d.dxf"))
            doc = ezdxf.readfile(str(path))
            used = Counter(e.dxf.layer for e in doc.modelspace())
        self.assertEqual(used["PV-3D-MODULOS"], 6 * sum(t["modules"] for t in g["tables"]))
        self.assertTrue({"PV-3D-SUELO", "PV-3D-ESTRUCTURA", "PV-3D-ESTACION", "PV-3D-VALLADO"} <= set(used))

    def test_the_modules_rise_with_the_tilt_and_stand_on_the_front_clearance(self):
        g = geometry()
        doc = pv_model3d.build(g, PLANT["result"])
        zs = [v[2] for e in doc.modelspace() if e.dxf.layer == "PV-3D-MODULOS" for v in e.wcs_vertices()]
        self.assertAlmostEqual(min(zs), 0.5 - 0.03 * 0.94, delta=0.05)      # lowest edge: the clearance (the module is 30 mm thick)
        self.assertGreater(max(zs), min(zs) + 1.0)

    def test_a_layout_without_tables_is_refused_and_a_missing_clearance_means_ground_level(self):
        g = geometry()
        g["module"]["front_clearance_m"] = None
        self.assertGreater(len(list(pv_model3d.build(g, PLANT["result"]).modelspace())), 0)
        g["tables"] = []
        with self.assertRaises(ValueError):
            pv_model3d.build(g, PLANT["result"])
