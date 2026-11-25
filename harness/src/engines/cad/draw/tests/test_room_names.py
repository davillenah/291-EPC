"""The name of a room is the text inside it, kept as written, with an English key; a floor has an English key too (ROOF for a roof)."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from epc_draw.arch.model import Room, Text                              # noqa: E402
from epc_draw.arch.pipeline import Context, Hints, scale_for           # noqa: E402
from epc_draw.arch.recognizers.levels import key_of as floor_key, named  # noqa: E402
from epc_draw.arch.recognizers.room_names import key_of, name_rooms     # noqa: E402

SIZE = (3000.0, 2000.0)
CTX = Context(size=SIZE, scale=scale_for(SIZE, None), hints=Hints())


def _room(i: str, x0: float, y0: float, x1: float, y1: float) -> Room:
    return Room(i, (x1 - x0) * (y1 - y0), None, ((x0 + x1) / 2, (y0 + y1) / 2), [(x0, y0, x1, y1)])


class TestRoomNames(unittest.TestCase):
    def test_the_text_inside_a_room_names_it(self):
        rooms = [_room("r1", 0, 0, 500, 400), _room("r2", 500, 0, 900, 400)]
        texts = [Text("COCINA", (600.0, 200.0), 20.0), Text("DORMITORIO", (100.0, 200.0), 20.0), Text("12,5 m²", (150.0, 260.0), 12.0)]
        named_ = name_rooms(rooms, texts, CTX)
        self.assertEqual([(r.name, r.key) for r in named_], [("DORMITORIO", "BEDROOM"), ("COCINA", "KITCHEN")])

    def test_figures_scales_and_dimensions_are_not_names(self):
        rooms = [_room("r1", 0, 0, 500, 400)]
        texts = [Text("3.50", (100.0, 200.0), 10.0), Text("ESC. 1:100", (200.0, 200.0), 10.0), Text("12,5 m²", (300.0, 200.0), 10.0)]
        self.assertEqual(name_rooms(rooms, texts, CTX)[0].name, "")

    def test_a_room_with_no_text_keeps_no_name_and_a_name_with_no_key_keeps_its_name(self):
        rooms = [_room("r1", 0, 0, 500, 400)]
        self.assertEqual(name_rooms(rooms, [], CTX)[0].name, "")
        got = name_rooms(rooms, [Text("TALLER", (100.0, 200.0), 20.0)], CTX)[0]
        self.assertEqual((got.name, got.key), ("TALLER", ""))

    def test_the_tags_of_a_drawing_carry_area_and_floor_codes_that_are_not_the_name(self):
        rooms = [_room("r1", 0, 0, 500, 400)]
        for written, name in (("COCINA · 16 PB", "COCINA"), ("V DORMITORIO 1 · 16 PA V P", "DORMITORIO 1"), ("BAÑO 1 P PA · 4", "BAÑO 1")):
            self.assertEqual(name_rooms(rooms, [Text(written, (100.0, 200.0), 20.0)], CTX)[0].name, name, written)

    def test_usual_names_have_english_keys(self):
        for text, key in {"ESTAR - COMEDOR": "LIVING_DINING_ROOM", "BAÑO": "BATHROOM", "Estacionamiento": "GARAGE", "Habitación 2": "BEDROOM"}.items():
            self.assertEqual(key_of(text, CTX), key, text)


class TestFloorKeys(unittest.TestCase):
    def test_floors_have_english_keys(self):
        self.assertEqual([floor_key(t, i) for t, i in (("PLANTA BAJA", 0), ("PLANTA ALTA", 1), ("PLANTA 2", 2), ("SUBSUELO", -1))], ["GROUND_FLOOR", "FIRST_FLOOR", "SECOND_FLOOR", "BASEMENT"])

    def test_a_roof_has_a_key_and_no_floor_number(self):
        lv = named([Text("3 PLANTA DE AZOTEA", (1.0, 11.0))], (0.0, 0.0, 10.0, 10.0))
        self.assertEqual((lv.index, lv.key), (None, "ROOF"))

    def test_a_tag_gives_the_code_and_the_area_the_designer_wrote(self):
        rooms = [_room("r1", 0, 0, 500, 400), _room("r2", 500, 0, 900, 400)]
        texts = [Text("DORM. 1", (100.0, 200.0), 20.0), Text("PT-01 · 10,50 m²", (100.0, 170.0), 12.0), Text("P-02", (130.0, 120.0), 12.0), Text("ESTAR-COCINA", (600.0, 200.0), 20.0)]
        named_rooms = name_rooms(rooms, texts, CTX)
        self.assertEqual((named_rooms[0].name, named_rooms[0].code, named_rooms[0].written_m2), ("DORM. 1", "PT-01", 10.5))       # the door tag P-02 is not part of the name
        self.assertEqual((named_rooms[1].name, named_rooms[1].code, named_rooms[1].written_m2), ("ESTAR-COCINA", "", None))


if __name__ == "__main__":
    unittest.main()
