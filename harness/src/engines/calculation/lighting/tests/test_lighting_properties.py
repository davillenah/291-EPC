"""OPT-13: invariants of the lighting `run` over generated documents (seeded, standard library only).

Only values given in the document are used (target lux, coefficient of utilisation, reflectances), so no norm value is involved.
"""
import copy
import random
import unittest

from epc_lighting import run

SAMPLES = 60
LUMINAIRE = {"id": "L1", "name": "generated luminaire", "lamps": 2, "lamp_flux_lm": 2400, "power_w": 64}


def _document(rng):
    return {"schema_version": "1.0", "luminaires": [dict(LUMINAIRE, lamps=rng.randint(1, 4), lamp_flux_lm=rng.uniform(800, 6000), power_w=rng.uniform(20, 120))],
            "rooms": [{"id": "R1", "name": "generated", "width_m": rng.uniform(2, 20), "length_m": rng.uniform(2, 30), "height_m": rng.uniform(2.4, 6),
                       "target_lux": rng.uniform(100, 750), "luminaire": "L1", "coefficient_of_utilisation": rng.uniform(0.3, 0.95),
                       "reflectances": {"ceiling": 0.7, "walls": 0.5, "floor": 0.2}}]}


def _room(document):
    return run(copy.deepcopy(document)).as_dict()["rooms"][0]


class LightingProperties(unittest.TestCase):
    def test_a_bigger_room_never_needs_fewer_luminaires(self):
        rng = random.Random(11)
        for _ in range(SAMPLES):
            doc = _document(rng)
            bigger = copy.deepcopy(doc)
            bigger["rooms"][0]["width_m"] *= 1.5
            with self.subTest(doc=doc):
                self.assertGreaterEqual(_room(bigger)["flux"]["luminaires_required"], _room(doc)["flux"]["luminaires_required"])

    def test_a_higher_target_never_needs_fewer_luminaires(self):
        rng = random.Random(12)
        for _ in range(SAMPLES):
            doc = _document(rng)
            brighter = copy.deepcopy(doc)
            brighter["rooms"][0]["target_lux"] *= 1.5
            with self.subTest(doc=doc):
                self.assertGreaterEqual(_room(brighter)["flux"]["luminaires_required"], _room(doc)["flux"]["luminaires_required"])

    def test_a_better_utilisation_never_needs_more_luminaires(self):
        rng = random.Random(13)
        for _ in range(SAMPLES):
            doc = _document(rng)
            doc["rooms"][0]["coefficient_of_utilisation"] = min(0.6, doc["rooms"][0]["coefficient_of_utilisation"])
            better = copy.deepcopy(doc)
            better["rooms"][0]["coefficient_of_utilisation"] *= 1.5
            with self.subTest(doc=doc):
                self.assertLessEqual(_room(better)["flux"]["luminaires_required"], _room(doc)["flux"]["luminaires_required"])

    def test_the_installed_luminaires_reach_the_target_and_the_power_follows_the_count(self):
        rng = random.Random(14)
        for _ in range(SAMPLES):
            doc = _document(rng)
            room = _room(doc)
            with self.subTest(doc=doc):
                self.assertGreaterEqual(room["verification"]["average_lux"], room["verification"]["target_lux"] - 1e-6)
                self.assertGreaterEqual(room["flux"]["luminaires_required"], room["flux"]["luminaires_exact"] - 1e-9)
                power = doc["luminaires"][0]["power_w"]
                installed = room["energy"]["installed_power_w"] / power
                self.assertGreaterEqual(installed, room["flux"]["luminaires_required"] - 1e-3)
                self.assertAlmostEqual(installed, round(installed), delta=0.01)

    def test_the_same_document_gives_the_same_answer(self):
        rng = random.Random(15)
        for _ in range(10):
            doc = _document(rng)
            self.assertEqual(run(copy.deepcopy(doc)).as_dict(), run(copy.deepcopy(doc)).as_dict())


if __name__ == "__main__":
    unittest.main()
