"""The equipment detail sheet of a PV plant: module, inverter and post views from the records; the reference values go to their own layer."""
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import ezdxf

from epc_drawing import pv_details, pv_parts

DATA = Path(__file__).resolve().parents[3] / "calculation" / "pv" / "src" / "epc_pv" / "data"


def parts():
    return {"module": pv_parts.find_record(DATA / "pv_modules", "cs6_2_54tm_1961x1134x30"),
            "inverters": {"INV-01": pv_parts.find_record(DATA / "pv_inverters", "sma.stp25000tl-30")},
            "structure": pv_parts.find_record(DATA / "mounting_structures" / "ground", "ramming_h_pile_fixed_table")}


class TestPvDetails(unittest.TestCase):
    def test_nothing_to_draw_gives_none(self):
        self.assertIsNone(pv_details.build({}))
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(pv_details.write({}, tmp, "PVT"))

    def test_module_cells_inverter_terminals_and_post_are_drawn_on_the_detail_layers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pv_details.write(parts(), tmp, "PVT", "es", "2026-11-20")
            self.assertTrue(path.name.endswith("_equipment_detail.dxf"))
            doc = ezdxf.readfile(str(path))
            used = Counter(e.dxf.layer for e in doc.modelspace())
        self.assertGreaterEqual(used["PV-DETALLE"], 108 + 3)               # the 108 cells, the three polygons of the H post, outlines
        self.assertGreater(used["PV-DETALLE-REF"], 0)                       # frame and junction box are not in the module record
        texts = " ".join(e.dxf.text for e in doc.modelspace() if e.dxftype() == "TEXT")
        self.assertIn("MÓDULO", texts)
        self.assertIn("REFERENCIA", texts)
