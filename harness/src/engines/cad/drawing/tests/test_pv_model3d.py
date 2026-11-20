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


DATA = Path(__file__).resolve().parents[3] / "calculation" / "pv" / "src" / "epc_pv" / "data"


def records():
    from epc_drawing import pv_parts
    return {"module": pv_parts.find_record(DATA / "pv_modules", "cs6_2_54tm_1961x1134x30"),
            "inverters": {"INV-01": pv_parts.find_record(DATA / "pv_inverters", "sma.stp25000tl-30")}}


class TestPvModel3dDetail(unittest.TestCase):
    def test_without_records_the_model_is_the_plain_one(self):
        g = geometry()
        used = Counter(e.dxf.layer for e in pv_model3d.build(g, PLANT["result"]).modelspace())
        self.assertFalse([k for k in used if k.startswith("PV-3D-REF")])

    def test_the_module_record_adds_frame_junction_box_and_cells_on_reference_layers(self):
        g = geometry()
        n = sum(t["modules"] for t in g["tables"])
        std = Counter(e.dxf.layer for e in pv_model3d.build(g, PLANT["result"], records()).modelspace())
        full = Counter(e.dxf.layer for e in pv_model3d.build(g, PLANT["result"], records(), "full").modelspace())
        self.assertEqual(std["PV-3D-MODULOS"], 6 * n)
        self.assertEqual(std["PV-3D-REF-FALLBACK"] >= 2 * 6 * n, True)       # the section and the box are not in the record: reference dimensions
        self.assertEqual(full["PV-3D-REF-UNVERIFIED"], 108 * n)              # 2 x (9 x 6) cells as printed in the record
        self.assertNotIn("PV-3D-REF-UNVERIFIED", std)
        low = Counter(e.dxf.layer for e in pv_model3d.build(g, PLANT["result"], records(), "low").modelspace())
        self.assertFalse([k for k in low if k == "PV-3D-REF-FALLBACK" and low[k] > 6])

    def test_the_inverter_record_sets_the_enclosure_size_and_hangs_the_terminals(self):
        g = geometry()
        doc = pv_model3d.build(g, PLANT["result"], records())
        inv = [v for e in doc.modelspace() if e.dxf.layer == "PV-3D-INVERSORES" for v in e.wcs_vertices()]
        self.assertAlmostEqual(max(v[0] for v in inv) - min(v[0] for v in inv), 0.661, places=3)
        self.assertAlmostEqual(max(v[2] for v in inv) - min(v[2] for v in inv), 0.682, places=3)
        used = Counter(e.dxf.layer for e in doc.modelspace())
        self.assertGreater(used["PV-3D-REF-TYPICAL"], 0)


class TestFoundation(unittest.TestCase):
    def zs(self, g, layer):
        doc = pv_model3d.build(g, PLANT["result"])
        return [v[2] for e in doc.modelspace() if e.dxf.layer == layer for v in e.wcs_vertices()]

    def test_nothing_goes_below_the_surface_unless_the_structure_record_states_a_depth(self):
        g = geometry()
        self.assertEqual(self.zs(g, "PV-3D-CIMENTACION"), [])
        self.assertGreaterEqual(min(self.zs(g, "PV-3D-ESTRUCTURA")), 0.0)
        g["foundation"] = {"structure_id": "driven_pile_fixed_table", "embedment_m": 1.5}
        self.assertAlmostEqual(min(self.zs(g, "PV-3D-CIMENTACION")), -1.5)
        self.assertGreaterEqual(min(self.zs(g, "PV-3D-ESTRUCTURA")), 0.0)
        g["foundation"] = {"structure_id": "roof_flat_slab_anchored", "embedment_m": None}
        self.assertEqual(self.zs(g, "PV-3D-CIMENTACION"), [])
