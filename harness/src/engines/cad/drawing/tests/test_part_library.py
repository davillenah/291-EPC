"""The part library: every equipment record with a geometry is drawn from its description (boxes, profile runs, features); what gives too little is skipped and listed."""
import json
import tempfile
import unittest
from pathlib import Path

import ezdxf

from epc_drawing import part_library

DATA = Path(__file__).resolve().parents[3] / "calculation" / "pv" / "src" / "epc_pv" / "data"


def records(folder):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((DATA / folder).glob("*.json"))]


BOX = {"id": "t", "geometry": {"elements": [{"id": "body", "kind": "enclosure", "position_mm": [0, 0, 0], "rotation_deg": [0, 0, 0], "size_mm": [1000, 500, 30], "status": "unverified"},
                                            {"id": "no_size", "kind": "other", "status": "unverified"}]},
       "features": [{"id": "dot", "kind": "dot", "on": "body", "face": "top", "position_mm": [10, 10], "size_mm": [8, 8], "depth_mm": 0.5, "status": "unverified"},
                    {"id": "nowhere", "kind": "dot", "on": "body", "face": "top", "size_mm": [8, 8]}]}


class TestPartLibrary(unittest.TestCase):
    def test_a_box_a_feature_and_what_gives_too_little(self):
        made = part_library.faces(BOX)
        self.assertEqual(len(made["faces"]["291-WS-ANNO-NOTE"]), 6)
        self.assertEqual(len(made["faces"][part_library.LAYER_FEATURE]), 6)
        self.assertEqual(sorted(made["skipped"]), ["no_size", "nowhere"])
        top = max(p[2] for f in made["faces"][part_library.LAYER_FEATURE] for p in f)
        self.assertAlmostEqual(top, 0.03 + 0.0005)      # the dot stands 0.5 mm proud of the top face

    def test_the_rotation_turns_the_element_about_its_position(self):
        rec = {"id": "r", "geometry": {"elements": [{"id": "b", "kind": "x", "position_mm": [0, 0, 0], "rotation_deg": [0, 0, 90], "size_mm": [1000, 100, 10], "status": "typical"}]}}
        pts = [p for f in part_library.faces(rec)["faces"]["291-WS-ANNO-SYMB"] for p in f]
        self.assertAlmostEqual(max(p[1] for p in pts), 1.0)
        self.assertAlmostEqual(min(p[0] for p in pts), -0.1)

    def test_every_record_of_the_pv_data_is_drawn_or_listed_and_the_library_opens(self):
        every = [r for d in ("pv_inverters/inverters", "pv_inverters/accessories", "pv_modules/formats", "pv_modules/technologies", "mounting_structures/ground", "mounting_structures/roof") for r in records(d)]
        with tempfile.TemporaryDirectory() as tmp:
            done = part_library.write(every, tmp, "LIB", stamp_date="2026-11-21")
            doc = ezdxf.readfile(str(done["dxf"]))
            macro = done["freecad"].read_text(encoding="utf-8")
        compile(macro, "macro", "exec")
        self.assertGreaterEqual(done["parts"], 40)
        self.assertEqual(len([b for b in doc.blocks if b.name.startswith("PV-PART-")]), done["parts"])
        self.assertTrue(all(k in {r["id"] for r in every} for k in done["skipped"]))
