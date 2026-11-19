"""The lux map of the lighting study: bands relative to the required level, lines of equal level, the figure blocks and the DXF of a floor."""
import json
import unittest
from pathlib import Path

import epc_lighting
from disciplines.electrical_lv import lux_map
from disciplines.electrical_lv.stages import rendering

EXAMPLE = Path(__file__).resolve().parents[2] / "src" / "engines" / "calculation" / "lighting" / "examples" / "classroom.json"


def result(grid=True):
    return epc_lighting.run(json.loads(EXAMPLE.read_text(encoding="utf-8")), epc_lighting.Options(return_grid=grid)).as_dict()


class LuxMapTests(unittest.TestCase):
    def test_scale_runs_from_the_first_to_the_last_colour_by_ratio(self):
        stops = lux_map.look()["scale"]
        self.assertEqual(lux_map.colour_at(-1, stops), stops[0]["color"])
        self.assertEqual(lux_map.colour_at(99, stops), stops[-1]["color"])
        self.assertEqual(lux_map.colour_at(stops[2]["ratio"], stops)[0], "#")
        self.assertEqual(lux_map.colour_at(stops[2]["ratio"], stops), stops[2]["color"])

    def test_refine_keeps_the_values_at_the_walls_and_the_cell_count(self):
        grid = {"nx": 2, "ny": 1, "maintained_lux": [10.0, 30.0]}
        fine = lux_map.refine(grid, 4)
        self.assertEqual((fine["nx"], fine["ny"], len(fine["maintained_lux"])), (8, 4, 32))
        self.assertEqual(fine["maintained_lux"][0], 10.0)
        self.assertEqual(fine["maintained_lux"][7], 30.0)
        self.assertEqual(lux_map.refine(grid, 1), grid)

    def test_room_map_cells_lines_and_reading(self):
        item = result()["rooms"][0]
        m = lux_map.room_map(item)
        grid = item["points"]["grid"]
        self.assertEqual(len(m["cells"]), grid["nx"] * grid["ny"])
        self.assertEqual(len(lux_map.room_map(item, smooth=3)["cells"]), 9 * grid["nx"] * grid["ny"])
        self.assertEqual(m["target_lux"], item["target"]["value"])
        self.assertTrue(all(c["color"] == lux_map.colour_at(c["lux"] / m["target_lux"], lux_map.look()["scale"]) for c in m["cells"]))
        self.assertEqual({c["ratio"] for c in m["curves"]}, {0.5, 1.0, 2.0, 0.25, 0.75, 1.5} & {c["ratio"] for c in lux_map.look()["contours"]})
        for curve in m["curves"]:
            self.assertTrue(all(0 <= x <= m["length_m"] + 1e-6 and 0 <= y <= m["width_m"] + 1e-6 for x, y in curve["points"]))
        self.assertIn("lx", lux_map.reading(m, "en"))
        self.assertIn("Exigido", lux_map.reading(m, "es"))

    def test_no_grid_no_map_and_a_note(self):
        res = result(grid=False)
        self.assertIsNone(lux_map.room_map(res["rooms"][0]))
        blocks = lux_map.study_blocks(res, "en")
        self.assertEqual([b["type"] for b in blocks], ["p"])
        self.assertIn("photometry", blocks[0]["text"])

    def test_contour_of_a_known_grid(self):
        grid = {"nx": 2, "ny": 2, "maintained_lux": [0.0, 10.0, 0.0, 10.0]}
        lines = lux_map.contours(grid, 2.0, 2.0, 5.0)
        self.assertEqual(len(lines), 1)
        self.assertTrue(all(abs(x - 1.0) < 1e-9 for x, _ in lines[0]))

    def test_study_report_has_figures_in_both_languages(self):
        doc = {"result": result(), "engine": {"name": "epc_lighting", "version": "x"}}
        report_rooms = doc["result"]["rooms"]
        for language in ("en", "es"):
            report = rendering.to_report("lighting_study", doc, "P", language)
            self.assertEqual(sum(b["type"] == "figure" for b in report["blocks"]), len(report_rooms))
        self.assertIn("Mapa de lux", json.dumps(rendering.to_report("lighting_study", doc, "P", "es"), ensure_ascii=False))

    def test_floor_map_is_laid_in_the_box(self):
        item = result()["rooms"][0]
        room = {"id": item["id"], "width_m": item["geometry"]["width_m"], "length_m": item["geometry"]["length_m"]}
        from disciplines.electrical_lv.intake.routing import to_plan
        fm = lux_map.floor_map([item], {item["id"]: [10.0, 20.0, 16.0, 24.0]}, {item["id"]: room}, to_plan)
        xs = [c["rect"][0] for c in fm["rooms"][0]["cells"]] + [c["rect"][2] for c in fm["rooms"][0]["cells"]]
        self.assertAlmostEqual(min(xs), 10.0)
        self.assertAlmostEqual(max(xs), 16.0)

    def test_dxf_has_cells_lines_and_labels(self):
        import tempfile
        import ezdxf
        import epc_plan.core as core
        import epc_plan.dxfout as dxfout
        item = result()["rooms"][0]
        room = {"id": item["id"], "width_m": item["geometry"]["width_m"], "length_m": item["geometry"]["length_m"]}
        from disciplines.electrical_lv.intake.routing import to_plan
        fm = lux_map.floor_map([item], {item["id"]: [0.0, 0.0, 6.0, 4.0]}, {item["id"]: room}, to_plan)
        doc = {"schema_version": "1.0", "plan": {"id": "t", "scale": {"p1": [0, 0], "p2": [1, 0], "distance_m": 1}}, "discipline": "electrica_BT", "nodes": [{"id": "TB-01", "kind": "TB", "x": 0.5, "y": 0.5}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.dxf"
            dxfout.write_dxf(core.process(doc), path, luxmap=fm)
            kinds = [e.dxftype() for e in ezdxf.readfile(str(path)).modelspace()]
        self.assertEqual(kinds.count("SOLID"), len(fm["rooms"][0]["cells"]) + len(fm["bar"]["cells"]))
        self.assertGreater(kinds.count("LWPOLYLINE"), 0)
        self.assertGreater(kinds.count("TEXT"), 0)


if __name__ == "__main__":
    unittest.main()
