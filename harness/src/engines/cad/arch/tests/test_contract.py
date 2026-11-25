"""OPT-02 (ADR-0040): `building_solids` and `draw_elevation` give what the lower-level calls give."""
import re
import tempfile
import unittest
from pathlib import Path

from epc_arch import ElevationInput, FloorInput, building_solids, draw_elevation, model3d, sections

BACKDROP = {"walls": [{"a": [0, 0], "b": [6, 0], "thickness_m": 0.2}, {"a": [6, 0], "b": [6, 4], "thickness_m": 0.2},
                      {"a": [6, 4], "b": [0, 4], "thickness_m": 0.2}, {"a": [0, 4], "b": [0, 0], "thickness_m": 0.2}],
            "openings": [{"kind": "door", "at": [3, 0], "width_m": 0.9, "angle": 0}]}
HEIGHTS = {"elevation_m": 0.0, "wall_height_m": 2.8, "door_head_m": 2.1, "window_sill_m": 0.9, "window_head_m": 2.1, "slab_m": 0.2}


def _stable(data):
    data = re.sub(rb"\d{4}-\d\d-\d\dT[\d:.]+\+00:00", b"{TIME}", data)
    data = re.sub(rb"(\$TD\w+\r?\n\s*40\r?\n)[\d.]+", rb"\1{JULIAN}", data)
    return re.sub(rb"\{[0-9A-F-]{36}\}", b"{GUID}", data)


class TestContract(unittest.TestCase):
    def test_the_solids_are_those_of_the_lower_call(self):
        floor = FloorInput(backdrop=BACKDROP, floor="L0", heights=HEIGHTS)
        self.assertEqual(building_solids(floor), model3d.building_solids(model3d.from_backdrop(BACKDROP, "L0"), HEIGHTS))

    def test_the_elevation_file_is_that_of_the_lower_calls(self):
        floor = FloorInput(backdrop=BACKDROP, floor="L0", heights=HEIGHTS)
        with tempfile.TemporaryDirectory() as tmp:
            old, new = Path(tmp) / "old.dxf", Path(tmp) / "new.dxf"
            arch = model3d.from_backdrop(BACKDROP, "L0")
            sections.write_view_dxf(sections.elevation(arch, "S", HEIGHTS), arch, old)
            draw_elevation(ElevationInput(floor=floor, side="S"), new)
            self.assertEqual(_stable(old.read_bytes()), _stable(new.read_bytes()))

    def test_the_inputs_are_frozen_and_checked(self):
        with self.assertRaises(Exception):
            FloorInput(backdrop={}, floor="L0", heights={}).floor = "L1"
        with self.assertRaises(TypeError):
            building_solids({"floor": "L0"})
        with self.assertRaises(TypeError):
            draw_elevation({"side": "S"}, "x.dxf")


if __name__ == "__main__":
    unittest.main()
