import unittest

from epc_draw.plan import scene_blocks as B, scene3d

BOX = {"vertices": [[0, 0, 0], [2, 0, 0], [2, 1, 0], [0, 1, 0], [0, 0, 1], [2, 0, 1], [2, 1, 1], [0, 1, 1]],
       "faces": [[3, 2, 1, 0], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]}


def moved(mesh, dx, dy, dz=0.0):
    return {"vertices": [[x + dx, y + dy, z + dz] for x, y, z in mesh["vertices"]], "faces": mesh["faces"]}


def turned(mesh):
    """The mesh turned 90 degrees about the vertical axis through its first corner."""
    return {"vertices": [[-y, x, z] for x, y, z in mesh["vertices"]], "faces": mesh["faces"]}


def solid(ident, mesh, layer="ELEC-BANDEJA"):
    return {"id": ident, "tag": ident, "kind": "tray", "layer": layer, "mesh": mesh}


class Blocks(unittest.TestCase):
    def test_equal_shapes_share_a_block_wherever_they_are_and_whichever_way_they_point(self):
        out = B.group([solid("a", BOX), solid("b", moved(BOX, 5, 3, 2)), solid("c", moved(turned(BOX), 1, 1))])
        self.assertEqual(len(out["blocks"]), 1)
        self.assertEqual([i["block"] for i in out["inserts"]], [out["blocks"][0]["name"]] * 3)

    def test_a_different_shape_is_another_block(self):
        bigger = {"vertices": [[x * 2, y, z] for x, y, z in BOX["vertices"]], "faces": BOX["faces"]}
        self.assertEqual(len(B.group([solid("a", BOX), solid("b", bigger)])["blocks"]), 2)

    def test_an_insertion_gives_the_mesh_back(self):
        mesh = moved(turned(BOX), 4, 2, 1)
        out = B.group([solid("a", mesh)])
        block, ins = out["blocks"][0], out["inserts"][0]
        r = ins["rotation"]
        back = [B._turn(v, r) for v in block["vertices"]]
        back = [[round(c + o, 3) for c, o in zip(p, ins["at"])] for p in back]
        self.assertEqual(back, [[round(c, 3) for c in v] for v in mesh["vertices"]])

    def test_the_same_solids_give_the_same_blocks(self):
        s = [solid("a", BOX), solid("b", moved(BOX, 1, 1))]
        self.assertEqual(B.group(s), B.group(s))


class InTheDxf(unittest.TestCase):
    def test_the_dxf_holds_blocks_and_insertions_not_loose_faces(self):
        import tempfile
        from pathlib import Path
        import ezdxf
        scene = {"schema_version": "1.0", "units": "m", "solids": [solid(f"t{i}", moved(BOX, 3 * i, 0)) for i in range(5)], "box": None}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.dxf"
            self.assertEqual(scene3d.write_dxf(scene, path, stamp_date="2026-11-24"), 30)
            kinds = {e.dxftype() for e in ezdxf.readfile(str(path)).modelspace()}
        self.assertEqual(kinds, {"INSERT"})


if __name__ == "__main__":
    unittest.main()
