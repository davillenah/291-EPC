"""The shading abacus drawing: a block per cell, the grid, the profile and the legend, with the viewport, in both languages, same bytes every time."""
import io
import unittest
from concurrent.futures import ThreadPoolExecutor

import ezdxf

from epc_draw.pv import abacus


def sample():
    cell = lambda cid, cover, x0: {"id": cid, "band": cid[0], "weight_pct": 3.5, "cover": cover, "outline": [[x0, 10.0], [x0 + 15, 10.0], [x0 + 15, 30.0], [x0, 30.0]]}
    return {"latitude_deg": -34.6, "tilt_deg": 30.0, "azimuth_deg": 0.0, "loss_pct": 1.5, "profile": [[-60.0, 0.0], [-10.0, 45.0], [10.0, 45.0], [60.0, 0.0]],
            "cells": [cell("A1", 0.0, 0.0), cell("A2", 0.5, -15.0), cell("A3", 1.0, -30.0), cell("B1", 0.25, 15.0), cell("B2", 0.75, 30.0)]}


def read(data):
    return ezdxf.read(io.StringIO(data.decode()))


class TestPvAbacus(unittest.TestCase):
    def test_one_file_with_its_name_and_the_viewport(self):
        out = abacus.render(sample(), "DEMO", "en")
        self.assertEqual(list(out), ["DEMO_shading_abacus.dxf"])
        doc = read(out["DEMO_shading_abacus.dxf"])
        self.assertIn("0-Viewport", doc.layers)
        self.assertTrue([e for e in doc.layout("Layout1") if e.dxf.layer == "0-Viewport"])

    def test_every_cell_is_a_block_inserted_in_the_model(self):
        doc = read(abacus.render(sample(), "D", "en")["D_shading_abacus.dxf"])
        names = {b.name for b in doc.blocks}
        for expected in ("PVA-CELL-A1", "PVA-CELL-A2", "PVA-CELL-B2", "PVA-GRID", "PVA-PROFILE", "PVA-LEGEND"):
            self.assertIn(expected, names)
        inserted = {e.dxf.name for e in doc.modelspace() if e.dxftype() == "INSERT"}
        self.assertTrue({n for n in names if n.startswith("PVA-")} <= inserted)
        self.assertFalse([e for e in doc.modelspace() if e.dxftype() in ("HATCH", "LINE", "LWPOLYLINE", "CIRCLE")])

    def test_only_the_hidden_cells_have_a_fill(self):
        doc = read(abacus.render(sample(), "D", "en")["D_shading_abacus.dxf"])
        fills = lambda cid: [e for e in doc.blocks.get(f"PVA-CELL-{cid}") if e.dxftype() == "HATCH"]
        self.assertEqual(fills("A1"), [])
        self.assertEqual(len(fills("A3")), 1)

    def test_the_layers_are_the_abacus_roles_of_the_catalog(self):
        doc = read(abacus.render(sample(), "D", "en")["D_shading_abacus.dxf"])
        for name in ("291-WP-ABAC-CELL", "291-WP-ABAC-COVR", "291-WP-ABAC-PROF", "291-WP-ABAC-TEXT"):
            self.assertIn(name, doc.layers)

    def test_the_two_languages_differ(self):
        en, es = (abacus.render(sample(), "D", lang)["D_shading_abacus.dxf"].decode() for lang in ("en", "es"))
        self.assertIn("SHADING ABACUS", en)
        self.assertIn("ÁBACO DE ASOLEAMIENTO", es)

    def test_no_profile_draws_no_line(self):
        data = sample()
        data["profile"] = []
        doc = read(abacus.render(data, "D", "en")["D_shading_abacus.dxf"])
        self.assertEqual([e for e in doc.blocks.get("PVA-PROFILE")], [])

    def test_same_bytes_on_four_threads(self):
        once = abacus.render(sample(), "D", "en", "2026-11-26")
        with ThreadPoolExecutor(4) as pool:
            for got in pool.map(lambda _: abacus.render(sample(), "D", "en", "2026-11-26"), range(4)):
                self.assertEqual(got, once)


if __name__ == "__main__":
    unittest.main()
