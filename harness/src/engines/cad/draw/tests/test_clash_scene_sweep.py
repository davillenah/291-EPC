"""The sweep that finds the pairs worth comparing in `clash_scene.detect` gives the very same clashes as comparing every pair, and the DXF file check counts what was written."""
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from epc_draw import plan as epc_plan   # noqa: E402
from epc_draw.plan import clash_scene   # noqa: E402


def block(ident, kind, x, y, z, size):
    vertices = [[x + dx * size[0], y + dy * size[1], z + dz * size[2]] for dx in (0, 1) for dy in (0, 1) for dz in (0, 1)]
    faces = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
    return {"id": ident, "tag": ident, "kind": kind, "layer": "L", "level": "L0", "mesh": {"vertices": vertices, "faces": faces}}


def scene(seed, n):
    rng = random.Random(seed)
    kinds = ["tray", "tray", "wall", "pipe"]
    return {"solids": [block(f"S{i}", rng.choice(kinds), rng.uniform(0, 30), rng.uniform(0, 30), rng.uniform(0, 3), (rng.uniform(0.1, 4), rng.uniform(0.1, 4), rng.uniform(0.1, 1))) for i in range(n)]}


def every_pair(sc, clearance):
    solids = [s for s in sc["solids"] if s["kind"] != "room"]
    hits = [(a, b, clash_scene._pair(a, b, clearance)) for i, a in enumerate(solids) for b in solids[i + 1:] if clash_scene._relevant(a, b)]
    found = [clash_scene._entry(a, b, hit) for a, b, hit in hits if hit is not None]
    return sorted(found, key=lambda c: (c["type"] != "hard", c["gap_m"], c["id"]))


class TestSweep(unittest.TestCase):
    def test_same_clashes_as_comparing_every_pair(self):
        for seed in range(5):
            sc = scene(seed, 120)
            for clearance in (0.0, 0.3):
                self.assertEqual(clash_scene.detect(sc, clearance), every_pair(sc, clearance))

    def test_the_scenes_have_clashes_to_compare(self):
        self.assertGreater(len(clash_scene.detect(scene(1, 120), 0.3)), 10)


class TestDxfCheck(unittest.TestCase):
    def test_the_file_check_counts_the_faces_and_polylines_written(self):
        piece = epc_plan.tray_pieces()[0]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.dxf"
            self.assertEqual(epc_plan.write_dxf_3d([piece], path), [])
            from epc_draw.plan import solid
            self.assertEqual(solid._entities_written(path), 1 + len(piece["mesh"]["faces"]))
