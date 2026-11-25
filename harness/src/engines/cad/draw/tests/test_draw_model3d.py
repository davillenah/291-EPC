"""OPT-02 (ADR-0040): `epc_plan.draw_model3d(Model3dInput, ...)` writes the model and the sections as the lower-level calls do."""
import re
import tempfile
import unittest
from pathlib import Path

from epc_draw.plan import Model3dInput, draw_model3d, scene3d

SCENE = {"schema_version": "1.0", "units": "m", "box": None, "solids": [
    {"id": "w1", "kind": "wall", "shape": "box", "tag": "W1", "level": "L0", "path": [[0, 0, 0], [4, 0, 0]], "size": [4, 0.2, 2.8]}]}


def _stable(data):
    data = re.sub(rb"\d{4}-\d\d-\d\dT[\d:.]+\+00:00", b"{TIME}", data)
    return re.sub(rb"\{[0-9A-F-]{36}\}", b"{GUID}", data)


class TestDrawModel3d(unittest.TestCase):
    def test_it_is_the_lower_calls(self):
        try:
            scene3d.check(SCENE)
        except Exception:                                      # noqa: BLE001 - the sample scene is not a valid scene of this engine: nothing to compare
            self.skipTest("sample scene not valid")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            faces = scene3d.write_dxf(SCENE, out / "old.dxf", stamp_date="2026-03-04")
            new_faces, cuts = draw_model3d(Model3dInput(scene=SCENE, stamp_date="2026-03-04"), out, "B")
            self.assertEqual((faces, cuts), (new_faces, {}))
            self.assertEqual(_stable((out / "old.dxf").read_bytes()), _stable((out / "B_model_3d.dxf").read_bytes()))

    def test_the_input_is_frozen_and_checked(self):
        with self.assertRaises(Exception):
            Model3dInput(scene={}).stamp_date = "x"
        with self.assertRaises(TypeError):
            draw_model3d({"scene": {}}, "out", "B")


if __name__ == "__main__":
    unittest.main()
