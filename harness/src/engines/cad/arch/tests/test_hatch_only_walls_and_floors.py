"""Only the walls and the floors are filled (HATCH in the DXF): openings, doors, windows, the scale bar and the north arrow are drawn with lines, and a wall is not painted across a door or a window."""
import io
import sys
import unittest
from pathlib import Path

import ezdxf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from epc_arch import Options, recognize                          # noqa: E402
from epc_arch.drawing import Poly, _solid_pieces, build_drawing                # noqa: E402
from epc_arch.export.export_dxf import to_dxf                    # noqa: E402
import helpers                                                    # noqa: E402

FILLED = {"A-WALL-FILL", "A-ROOM"}


class TestHatchOnlyWallsAndFloors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.arch = recognize(helpers.room_dxf(), "flat.dxf", Options()).architecture
        cls.drawing = build_drawing(cls.arch, sheet="A3")

    def test_only_walls_and_floors_are_filled(self):
        filled = {it.layer for it in self.drawing.items if isinstance(it, Poly) and it.fill}
        self.assertTrue(filled)
        self.assertLessEqual(filled, FILLED)

    def test_the_dxf_has_hatches_only_on_those_layers(self):
        doc = ezdxf.read(io.StringIO(to_dxf(self.drawing)))
        layers = {e.dxf.layer for e in doc.modelspace() if e.dxftype() == "HATCH"}
        self.assertTrue(layers)
        self.assertLessEqual(layers, FILLED)

    def test_a_wall_is_cut_where_an_opening_interrupts_it(self):
        self.assertEqual(_solid_pieces(0.0, 10.0, [(3.0, 4.0), (6.0, 8.0)]), [(0.0, 3.0), (4.0, 6.0), (8.0, 10.0)])
        self.assertEqual(_solid_pieces(0.0, 10.0, []), [(0.0, 10.0)])
        self.assertEqual(_solid_pieces(0.0, 10.0, [(-1.0, 11.0)]), [])
        self.assertEqual(_solid_pieces(0.0, 10.0, [(2.0, 5.0), (4.0, 6.0)]), [(0.0, 2.0), (6.0, 10.0)])

    def test_the_wall_pieces_of_the_room_leave_its_door_free(self):
        pieces = [it for it in self.drawing.items if isinstance(it, Poly) and it.layer == "A-WALL-FILL"]
        self.assertGreater(len(pieces), 4)                                       # four walls, and more where the door and the window cut one


if __name__ == "__main__":
    unittest.main()
