"""The parts library of the tray system, all by code (epc_plan.tray_pieces)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import epc_plan   # noqa: E402


class TestTrayLibrary(unittest.TestCase):
    def setUp(self):
        self.items = epc_plan.tray_pieces(0.3, 0.09)
        self.by_code = {p["code"]: p for p in self.items}

    def test_every_kind_has_its_straight_and_fittings(self):
        for kind in ("ESC", "PER", "CIE", "ALA", "CAN"):
            for fitting in ("", "C90", "C45", "CV", "T", "X", "RC", "RL", "CAJ", "FIN", "UN", "TP"):
                code = "-".join(x for x in ("BN", kind, fitting, "300x90") if x)
                if kind == "ALA" and fitting == "TP":
                    continue                                                   # a wire-mesh tray takes no cover
                self.assertIn(code, self.by_code)

    def test_supports_and_fasteners_are_there(self):
        for code in ("BN-ESC-MP-300x90", "BN-ESC-MR-300x90", "SB-TRA-300x90", "SB-VR-M10x500", "SB-PRF-41x41x1000", "SB-GRA-M10", "SB-PLT-M10", "SB-BUL-M8x25", "SB-TUE-M8", "SB-ARA-M8", "SB-MAN-M10"):
            self.assertIn(code, self.by_code)

    def test_codes_are_unique_bilingual_and_every_piece_has_faces(self):
        self.assertEqual(len(self.by_code), len(self.items))
        for p in self.items:
            self.assertTrue(p["name"]["en"] and p["name"]["es"])
            self.assertTrue(p["mesh"]["faces"])
            self.assertTrue(all(3 <= len(f) <= 4 for f in p["mesh"]["faces"]))
            self.assertTrue(all(0 <= i < len(p["mesh"]["vertices"]) for f in p["mesh"]["faces"] for i in f))

    def test_everything_of_the_maker_catalogue_has_a_part_of_ours(self):
        wanted = ["BN-ESC-TC90-300x90", "BN-ESC-TC45-300x90", "BN-ESC-TCA-300x90", "BN-ESC-TT-300x90", "BN-ESC-TX-300x90", "BN-ESC-TV-300x90", "BN-ESC-MG-300x90", "BN-ESC-UNL-300x90",
                  "BN-ESC-UA-300x90", "SB-PUM-100x100", "SB-BUC-M8x25", "SB-BUC-3-8x25", "SB-RET-M8", "SB-GSU-M10", "SB-GFI-M8", "SB-GPT-M8"]
        for code in wanted:
            self.assertIn(code, self.by_code)
        self.assertNotIn("BN-ALA-TP-300x90", self.by_code)                      # a wire-mesh tray takes no cover

    def test_a_piece_is_written_to_dxf_with_its_own_mesh(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "piece.dxf"
            self.assertEqual(epc_plan.write_dxf_3d([self.by_code["SB-BUL-M8x25"]], path), [])
            self.assertTrue(path.stat().st_size > 0)

    def test_a_wrong_size_is_an_error(self):
        with self.assertRaises(epc_plan.PlanError):
            epc_plan.tray_pieces(0, 0.09)


if __name__ == "__main__":
    unittest.main()
