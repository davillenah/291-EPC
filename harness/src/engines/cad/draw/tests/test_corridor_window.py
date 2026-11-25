"""A corridor that ends in a window: the stretch between the two walls that close the corridor looks like a passage, but the panes across it and the outside beyond make it a window,
and the corridor is a room (it used to stay open to the outside and was lost)."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

spec = importlib.util.spec_from_file_location("planta_prueba", HERE.parent / "scripts" / "planta_prueba.py")
pp = importlib.util.module_from_spec(spec)
sys.modules["planta_prueba"] = pp
spec.loader.exec_module(pp)
from epc_draw import arch as epc_arch  # noqa: E402

W, H = 2000, 1200
WALLS = [("m-n", (0, 0), (W, 0), 30), ("m-e", (W, 0), (W, H), 30), ("m-s", (W, H), (0, H), 30), ("m-o", (0, H), (0, 0), 30), ("m-c1", (0, 500), (W, 500), 15), ("m-c2", (0, 700), (W, 700), 15)]
WALLS += [(f"m-d{i}", (500 * i, 0), (500 * i, 500), 15) for i in (1, 2, 3)] + [(f"m-s{i}", (500 * i, 700), (500 * i, H), 15) for i in (1, 2, 3)]


def plan(end):
    """Four rooms on each side of a corridor; `end` is the opening at the west end of the corridor: a window or a door."""
    ab = [(f"PN{i + 1}", "puerta", "m-c1", 250 + 500 * i, 90, "a", -1) for i in range(4)] + [(f"PS{i + 1}", "puerta", "m-c2", 250 + 500 * i, 90, "a", 1) for i in range(4)]
    ab += [(f"VN{i + 1}", "ventana", "m-n", 250 + 500 * i, 150, None, 0) for i in range(4)] + [(f"VS{i + 1}", "ventana", "m-s", 250 + 500 * i, 150, None, 0) for i in range(4)]
    ab += [("PENT", "puerta", "m-o", 600, 120, "a", 1)] if end == "door" else [("VO", "ventana", "m-o", 600, 120, None, 0)]
    amb = [(f"OFICINA {i}", (500 * i, 0, 500 * i + 500, 500)) for i in range(4)] + [("PASILLO", (0, 500, W, 700))] + [(f"LOCAL {i}", (500 * i, 700, 500 * i + 500, H)) for i in range(4)]
    return {"titulo": "t", "estilo": "relleno", "ancho": W, "alto": H, "muros": WALLS, "aberturas": ab, "ambientes": amb, "mobiliario": []}


def recognise(end):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "planta.dxf"
        pp.dxf(plan(end), path)
        return epc_arch.recognize(path.read_bytes(), "planta.dxf").architecture.as_dict()


class CorridorWindow(unittest.TestCase):
    def test_a_window_at_the_end_of_the_corridor_is_found_and_the_corridor_is_a_room(self):
        got = recognise("window")
        self.assertEqual((got["counts"]["windows"], got["counts"]["doors"]), (9, 8))
        self.assertIn("PASILLO", [r["name"] for r in got["rooms"]])
        self.assertEqual(len(got["rooms"]), 9)

    def test_a_door_at_the_end_still_gives_the_same_rooms(self):
        got = recognise("door")
        self.assertEqual((got["counts"]["windows"], got["counts"]["doors"]), (8, 9))
        self.assertEqual(len(got["rooms"]), 9)

    def test_without_panes_a_corridor_end_stays_an_empty_passage(self):
        got = recognise("window")
        # the same plan with the corridor end left open (no window drawn) must not invent one
        p = plan("window")
        p["aberturas"] = [a for a in p["aberturas"] if a[0] != "VO"] + [("HO", "hueco", "m-o", 600, 120, None, 0)]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "planta.dxf"
            pp.dxf(p, path)
            open_end = epc_arch.recognize(path.read_bytes(), "planta.dxf").architecture.as_dict()
        self.assertEqual(open_end["counts"]["windows"], 8)
        self.assertEqual(got["counts"]["windows"], 9)


if __name__ == "__main__":
    unittest.main()
