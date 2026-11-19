"""Roof planes read from an ASCII DXF: planes, obstacles in plane coordinates, tilt and azimuth from text, units, refusals in both languages."""
import unittest

from epc_pv import PvError, plan_roof, roofdxf
from test_roof import ARRAY


def dxf(entities, units=6):
    head = f"0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n{units}\n0\nENDSEC\n" if units is not None else "0\nSECTION\n2\nHEADER\n0\nENDSEC\n"
    return head + "0\nSECTION\n2\nENTITIES\n" + "".join(entities) + "0\nENDSEC\n0\nEOF\n"


def rect(layer, x0, y0, x1, y1):
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return f"0\nLWPOLYLINE\n8\n{layer}\n90\n4\n70\n1\n" + "".join(f"10\n{x}\n20\n{y}\n" for x, y in pts)


def text(layer, x, y, s):
    return f"0\nTEXT\n8\n{layer}\n10\n{x}\n20\n{y}\n40\n0.2\n1\n{s}\n"


class TestRoofDxf(unittest.TestCase):
    def test_a_plane_with_tilt_and_azimuth_and_an_obstacle(self):
        got = roofdxf.read(dxf([rect("PV-CUBIERTA", 0, 0, 10, 5), text("PV-CUBIERTA-DATOS", 1, 1, "tilt=30 az=180"), rect("PV-CUBIERTA-OBST", 4, 1, 5, 2)]), 0.5)
        p = got["planes"][0]
        self.assertEqual((p["id"], p["width_m"], p["tilt_deg"], p["azimuth_deg"]), ("R1", 10.0, 30.0, 180.0))
        self.assertAlmostEqual(p["slope_m"], 5 / 0.8660254, places=3)
        self.assertEqual(p["obstacles"][0]["x"], 4.0)
        self.assertEqual(got["warnings"], [])

    def test_the_eave_is_the_edge_on_the_facing_side(self):
        # facing north (azimuth 0): the eave is the north edge, an obstacle near the north edge is near y = 0 of the plane
        got = roofdxf.read(dxf([rect("PV-CUBIERTA", 0, 0, 10, 5), text("PV-CUBIERTA-DATOS", 1, 1, "tilt=0 az=0"), rect("PV-CUBIERTA-OBST", 4, 4, 5, 5)]), 0.5)
        ob = got["planes"][0]["obstacles"][0]
        self.assertEqual((ob["x"], ob["y"]), (5.0, 0.0))
        east = roofdxf.read(dxf([rect("PV-CUBIERTA", 0, 0, 10, 5), text("PV-CUBIERTA-DATOS", 1, 1, "tilt=0 az=90")]), 0.5)["planes"][0]
        self.assertEqual((east["width_m"], east["slope_m"]), (5.0, 10.0))

    def test_no_data_leaves_tilt_and_azimuth_to_the_harness_and_says_so(self):
        got = roofdxf.read(dxf([rect("PV-CUBIERTA", 0, 0, 6, 4)]), 0.5)
        self.assertNotIn("tilt_deg", got["planes"][0])
        self.assertEqual({w["code"] for w in got["warnings"]}, {"roof_dxf_azimuth", "roof_dxf_tilt"})
        self.assertTrue(all(w["es"] for w in got["warnings"]))

    def test_planes_are_numbered_top_to_bottom_and_millimetres_are_converted(self):
        got = roofdxf.read(dxf([rect("PV-CUBIERTA", 0, 0, 4000, 3000), rect("PV-CUBIERTA", 0, 5000, 6000, 8000)], units=4), 0.5)
        self.assertEqual([(p["id"], p["width_m"]) for p in got["planes"]], [("R1", 6.0), ("R2", 4.0)])

    def test_two_planes_become_two_arrays_through_the_roof_engine(self):
        planes = roofdxf.read(dxf([rect("PV-CUBIERTA", 0, 0, 10, 5), text("PV-CUBIERTA-DATOS", 1, 1, "tilt=25 az=0"),
                                   rect("PV-CUBIERTA", 12, 0, 20, 5), text("PV-CUBIERTA-DATOS", 13, 1, "tilt=20 az=90")]), 0.5)["planes"]
        result = plan_roof({"planes": planes, "module_dimensions_mm": [2278, 1134], "module_gap_m": 0.02, "array": dict(ARRAY)})
        self.assertEqual({a["id"]: (a["tilt_deg"], a["azimuth_deg"]) for a in result["arrays"]}, {"R1": (25.0, 0.0), "R2": (20.0, 90.0)})
        self.assertEqual(len(result["arrays"]), 2)

    def test_refusals_are_in_both_languages(self):
        cases = [dxf([rect("PV-CUBIERTA", 0, 0, 6, 4)], units=None), dxf([]), dxf([rect("PV-CUBIERTA", 0, 0, 6, 4), text("PV-CUBIERTA-DATOS", 1, 1, "az=45")]), "AutoCAD Binary DXF\r\n"]
        for case in cases:
            with self.assertRaises(PvError) as caught:
                roofdxf.read(case, 0.5)
            self.assertTrue(caught.exception.en and caught.exception.es)
            self.assertNotEqual(caught.exception.en, caught.exception.es)

    def test_an_old_style_polyline_mtext_a_centred_text_and_a_closing_vertex(self):
        poly = "0\nPOLYLINE\n8\nPV-CUBIERTA\n70\n1\n" + "".join(f"0\nVERTEX\n8\nPV-CUBIERTA\n10\n{x}\n20\n{y}\n" for x, y in ((0, 0), (6, 0), (6, 4), (0, 4), (0, 0))) + "0\nSEQEND\n"
        mtext = "0\nMTEXT\n8\nPV-CUBIERTA-DATOS\n10\n1\n20\n1\n1\ntilt: 15,5\n"
        centred = "0\nTEXT\n8\nPV-CUBIERTA-DATOS\n10\n99\n20\n99\n11\n3\n21\n2\n1\naz=270\n"
        got = roofdxf.read(dxf([poly, mtext, centred]).encode("utf-8"), 0.5)["planes"][0]
        self.assertEqual((got["tilt_deg"], got["azimuth_deg"], got["width_m"]), (15.5, 270.0, 4.0))      # azimuth 270: the eave is the west edge, so the width is the north-south extent

    def test_a_stray_obstacle_is_ignored_and_said(self):
        got = roofdxf.read(dxf([rect("PV-CUBIERTA", 0, 0, 6, 4), rect("PV-CUBIERTA-OBST", 20, 20, 21, 21)]), 0.5)
        self.assertEqual([w["code"] for w in got["warnings"] if w["code"] == "roof_dxf_obstacles"], ["roof_dxf_obstacles"])

    def test_a_tilt_out_of_range_and_garbage_are_refused(self):
        for case in (dxf([rect("PV-CUBIERTA", 0, 0, 6, 4), text("PV-CUBIERTA-DATOS", 1, 1, "tilt=120")]), "not a dxf\nat all\n", "0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n6\n0\nENDSEC\n"):
            with self.assertRaises(PvError):
                roofdxf.read(case, 0.5)

    def test_a_polygon_that_is_not_a_rectangle_is_refused(self):
        tri = "0\nLWPOLYLINE\n8\nPV-CUBIERTA\n90\n3\n70\n1\n10\n0\n20\n0\n10\n5\n20\n0\n10\n0\n20\n5\n"
        with self.assertRaises(PvError):
            roofdxf.read(dxf([tri]), 0.5)


if __name__ == "__main__":
    unittest.main()
