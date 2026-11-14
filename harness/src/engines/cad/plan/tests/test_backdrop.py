"""The building under the services in the DXF: walls as closed outlines and room names as text, on layers of their own."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import ezdxf   # noqa: E402
from epc_plan import core, dxfout   # noqa: E402
from test_dxf_turn import drawing   # noqa: E402

BACKDROP = {"walls": [{"a": [0, 0], "b": [10, 0], "thickness_m": 0.2}, {"a": [10, 0], "b": [10, 5], "thickness_m": 0.2}, {"a": [3, 3], "b": [3, 3], "thickness_m": 0.2}],
            "rooms": [{"name": "OFFICE", "at": [5, 2.5]}]}


class TestBackdrop(unittest.TestCase):
    def write(self, backdrop):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.dxf"
            warnings = dxfout.write_dxf(core.process(drawing({})), path, backdrop=backdrop)
            return warnings, ezdxf.readfile(path).modelspace()

    def test_the_walls_are_closed_outlines_of_their_thickness_and_the_names_text(self):
        warnings, msp = self.write(BACKDROP)
        self.assertEqual(warnings, [])
        walls = [e for e in msp.query("LWPOLYLINE") if e.dxf.layer.endswith("ARQ-MUROS")]
        self.assertEqual(len(walls), 2)                        # the wall of length zero is left out
        xs = sorted({round(p[0], 3) for p in walls[0].get_points()})
        ys = sorted({round(p[1], 3) for p in walls[0].get_points()})
        self.assertEqual((xs, ys), ([0.0, 10.0], [-0.1, 0.1]))
        second = sorted({round(p[1], 3) for p in walls[1].get_points()})
        self.assertEqual([float(v) + 0.0 for v in second], [-5.0, 0.0])                   # the screen's y down becomes the DXF's y up, as for the nodes
        self.assertEqual([t.dxf.text for t in msp.query("TEXT") if t.dxf.layer.endswith("ARQ-LOCALES")], ["OFFICE"])
        self.assertEqual([round(t.dxf.insert[1], 3) for t in msp.query("TEXT") if t.dxf.layer.endswith("ARQ-LOCALES")], [-2.5])

    def test_without_a_backdrop_nothing_is_added(self):
        _, msp = self.write(None)
        self.assertFalse([e for e in msp if e.dxf.layer.endswith(("ARQ-MUROS", "ARQ-LOCALES"))])


if __name__ == "__main__":
    unittest.main()
