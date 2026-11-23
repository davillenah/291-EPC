"""OPT-13: invariants of the HVAC `run` over generated documents (seeded, standard library only). Values come from the document."""
import copy
import random
import unittest

from epc_hvac import run

SAMPLES = 80


def _document(rng):
    envelope = [{"kind": rng.choice(["wall", "roof", "floor"]), "u_w_m2k": rng.uniform(0.2, 3.0), "area_m2": rng.uniform(5, 100), "delta_t_k": rng.uniform(1, 20)}
                for _ in range(rng.randint(0, 3))]
    return {"design": {"t_out_c": 35, "t_in_c": 24, "w_out_kg_kg": 0.018, "w_in_kg_kg": 0.0093, "supply_delta_t_k": rng.uniform(6, 14)},
            "spaces": [{"id": "S1", "area_m2": rng.uniform(10, 300), "height_m": rng.uniform(2.4, 5), "use": "office", "occupants": rng.randint(0, 40),
                        "lighting_w_m2": rng.uniform(0, 25), "equipment_w_m2": rng.uniform(0, 40), "envelope": envelope}]}


def _totals(doc):
    return run(copy.deepcopy(doc)).as_dict()["totals"]


class HvacProperties(unittest.TestCase):
    def test_more_heat_never_lowers_the_load(self):
        rng = random.Random(21)
        for _ in range(SAMPLES):
            doc = _document(rng)
            base = _totals(doc)["total_w"]
            for key in ("occupants", "lighting_w_m2", "equipment_w_m2"):
                more = copy.deepcopy(doc)
                more["spaces"][0][key] = more["spaces"][0][key] * 1.5 + 1
                with self.subTest(doc=doc, grown=key):
                    self.assertGreaterEqual(_totals(more)["total_w"], base - 1e-6)

    def test_more_envelope_area_with_a_positive_difference_never_lowers_the_load(self):
        rng = random.Random(22)
        for _ in range(SAMPLES):
            doc = _document(rng)
            more = copy.deepcopy(doc)
            for item in more["spaces"][0]["envelope"]:
                item["area_m2"] *= 2
            with self.subTest(doc=doc):
                self.assertGreaterEqual(_totals(more)["total_w"], _totals(doc)["total_w"] - 1e-6)

    def test_the_totals_are_the_sum_of_the_spaces_and_the_parts(self):
        rng = random.Random(23)
        for _ in range(SAMPLES):
            doc = _document(rng)
            second = copy.deepcopy(doc["spaces"][0])
            second["id"] = "S2"
            second["area_m2"] *= 0.5
            doc["spaces"].append(second)
            out = run(copy.deepcopy(doc)).as_dict()
            with self.subTest(doc=doc):
                self.assertAlmostEqual(out["totals"]["total_w"], sum(s["total_w"] for s in out["spaces"]), delta=0.3)
                for space in out["spaces"]:
                    self.assertGreaterEqual(space["supply_ls"], 0)
                    self.assertAlmostEqual(space["total_w"], space["sensible_w"] + space["latent_w"], delta=0.3)

    def test_the_same_document_gives_the_same_answer(self):
        rng = random.Random(24)
        for _ in range(10):
            doc = _document(rng)
            self.assertEqual(run(copy.deepcopy(doc)).as_dict(), run(copy.deepcopy(doc)).as_dict())


if __name__ == "__main__":
    unittest.main()
