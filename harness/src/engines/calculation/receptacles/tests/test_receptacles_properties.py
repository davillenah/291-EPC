"""OPT-13: invariants of the receptacles `run` over generated documents (seeded, standard library only)."""
import copy
import random
import unittest

from epc_receptacles import run

SAMPLES = 80
USES = ("office", "warehouse", "kitchen", "general")


def _document(rng):
    return {"schema_version": "1.0",
            "receptacles": [{"id": "tug", "name": "outlet", "kind": "general", "poles": 2, "rated_a": 10, "power_va": rng.choice([100, 200, 300]), "height_m": 0.3, "ip": "IP20"}],
            "rooms": [{"id": "R1", "name": "generated", "use": rng.choice(USES), "length_m": rng.uniform(2, 40), "width_m": rng.uniform(2, 30), "receptacle": "tug"}]}


def _room(doc):
    return run(copy.deepcopy(doc)).as_dict()["rooms"][0]


class ReceptacleProperties(unittest.TestCase):
    def test_a_bigger_room_never_gets_fewer_outlets(self):
        rng = random.Random(31)
        for _ in range(SAMPLES):
            doc = _document(rng)
            bigger = copy.deepcopy(doc)
            bigger["rooms"][0]["length_m"] *= 2
            with self.subTest(doc=doc):
                self.assertGreaterEqual(_room(bigger)["required"], _room(doc)["required"])

    def test_the_load_is_the_outlets_times_their_power_and_nothing_is_missing(self):
        rng = random.Random(32)
        for _ in range(SAMPLES):
            doc = _document(rng)
            room = _room(doc)
            with self.subTest(doc=doc):
                self.assertGreaterEqual(room["installed"], room["required"])
                self.assertAlmostEqual(room["load_va"], room["installed"] * room["power_va_each"], delta=0.5)
                self.assertEqual(len(room["layout"]["positions"]), room["installed"])
                self.assertGreaterEqual(room["circuits_min"], 1)

    def test_a_higher_outlet_power_never_lowers_the_load(self):
        rng = random.Random(33)
        for _ in range(SAMPLES):
            doc = _document(rng)
            more = copy.deepcopy(doc)
            more["receptacles"][0]["power_va"] *= 2
            with self.subTest(doc=doc):
                self.assertGreaterEqual(_room(more)["load_va"], _room(doc)["load_va"])

    def test_the_same_document_gives_the_same_answer(self):
        rng = random.Random(34)
        for _ in range(10):
            doc = _document(rng)
            self.assertEqual(run(copy.deepcopy(doc)).as_dict(), run(copy.deepcopy(doc)).as_dict())


if __name__ == "__main__":
    unittest.main()
