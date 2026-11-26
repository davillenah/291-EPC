"""Every layer of a DXF made by the drawing pipelines is named in English by the NCS / AIA convention (`291-...`) or is `0-*`, and carries a description (owner rule)."""
import copy
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import ezdxf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import characterization as C  # noqa: E402
from epc_draw.pv import model3d as pv_model3d  # noqa: E402

NAME = re.compile(r"^(291-[A-Z]{1,2}(-[A-Z]{4}){1,3}(-[A-Z0-9])?|0-[A-Za-z]+(-[A-Za-z0-9]+)?)$")
PLANT = json.loads((HERE.parent.parent / "draw" / "tests" / "fixtures" / "pv_plant.json").read_text(encoding="utf-8"))


def problems(doc):
    layers = [lay for lay in doc.layers if lay.dxf.name not in ("0", "Defpoints")]
    return ([lay.dxf.name for lay in layers if not NAME.match(lay.dxf.name)], [lay.dxf.name for lay in layers if not lay.description], len(layers))


class LayerNameTests(unittest.TestCase):
    def check(self, doc, label):
        bad, undescribed, n = problems(doc)
        self.assertTrue(n, label)
        self.assertEqual(bad, [], label)
        self.assertEqual(undescribed, [], label)

    def test_sld_and_mld(self):
        work = Path(tempfile.mkdtemp(prefix="layerdesc_"))
        try:
            C.B.design(json.loads(json.dumps(C.SMALL)), work, "T1", None, None, 18, ("sld", "mld"))
            dxfs = sorted((work / "out").rglob("*.dxf"))
            self.assertTrue(dxfs)
            for p in dxfs:
                self.check(ezdxf.readfile(str(p)), p.name)
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_pv_model_3d(self):
        g = copy.deepcopy(PLANT["geometry"])
        g["module"] = {"dimensions_mm": [2278.0, 1134.0], "gap_m": 0.02, "front_clearance_m": 0.5}
        g["tilts_deg"] = {a["id"]: 20.0 for a in PLANT["result"]["arrays"]}
        for t in g["tables"]:
            t.setdefault("array", PLANT["result"]["arrays"][0]["id"])
        g["tilts_deg"].setdefault(g["tables"][0]["array"], 20.0)
        with tempfile.TemporaryDirectory() as tmp:
            self.check(ezdxf.readfile(str(pv_model3d.write(g, PLANT["result"], tmp, "PVT", stamp_date="2026-11-19"))), "pv_model_3d")


if __name__ == "__main__":
    unittest.main()
