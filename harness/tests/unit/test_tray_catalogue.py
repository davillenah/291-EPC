import unittest

from epc_plan import core, tray_catalogue as C


class TrayCatalogueTests(unittest.TestCase):
    def setUp(self):
        self.cat = core.PARAMS["tray_catalogue"]

    def test_the_rail_sheet_follows_the_height(self):
        self.assertEqual(C.rail_thickness_mm(self.cat, 90), 1.24)
        self.assertEqual(C.rail_thickness_mm(self.cat, 150), 2.10)

    def test_the_cover_sheet_follows_the_width(self):
        self.assertEqual(C.cover_thickness_mm(self.cat, 300, "Z"), 0.71)
        self.assertEqual(C.cover_thickness_mm(self.cat, 450, "Z"), 0.89)

    def test_sizes_start_with_the_smallest_free_section(self):
        first = C.fill_candidates(self.cat)[0]
        self.assertEqual((first["ancho_mm"], first["alto_mm"], first["ala_mm"]), (150.0, 44.0, 65.0))

    def test_the_drawing_takes_length_and_radius_from_the_catalogue(self):
        q = C.ladder(core.PARAMS["detail"]["ladder"], self.cat)
        self.assertEqual((q["joint_m"], q["elbow_radius_m"], q["vertical_links"], q["cover_wide_from_m"]), (3.0, 0.3, 5, 0.45))

    def test_the_thread_turns_follow_the_pitch(self):
        self.assertEqual(C.thread_turns(self.cat, "M6", 25), 25)
        self.assertEqual(C.thread_turns(self.cat, "3/8", 25), 15)

    def test_the_library_bolts_carry_one_ridge_per_turn(self):
        from epc_plan import tray_library
        faces = {p["code"]["code"] if isinstance(p["code"], dict) else p["code"]: len(p["mesh"]["faces"]) for p in tray_library._accessories(0.3, 0.09)}
        self.assertGreater(faces["SB-BUC-M6x25"], faces["SB-BUC-3-8x25"])


if __name__ == "__main__":
    unittest.main()
