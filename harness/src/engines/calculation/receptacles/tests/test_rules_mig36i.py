import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import epc_receptacles  # noqa: E402
from epc_receptacles import ReceptaclesError  # noqa: E402

TUG = {"id": "tug", "kind": "general", "power_va": 100, "height_m": 0.3}


def one(**kw):
    room = {"id": "R1", "receptacle": "tug", **kw}
    return epc_receptacles.run({"receptacles": [TUG], "rooms": [room]}).as_dict()["rooms"][0]


class TestBedroom(unittest.TestCase):
    """Owner verdict 2026-11-10 (r1): a bedroom under 10 m² gets 2 outlets."""

    def test_a_bedroom_under_10_m2_gets_two(self):
        self.assertEqual(one(use="bedroom", length_m=2.5, width_m=3.2)["required"], 2)       # 8 m²

    def test_the_limit_itself_and_larger_bedrooms_keep_three(self):
        self.assertEqual(one(use="bedroom", length_m=2.5, width_m=4)["required"], 3)         # exactly 10 m²
        self.assertEqual(one(use="bedroom", length_m=3, width_m=4)["required"], 3)           # 12 m²

    def test_other_rooms_do_not_follow_the_bedroom_exception(self):
        self.assertEqual(one(use="kitchen", length_m=2, width_m=3)["required"], 5)
        self.assertEqual(one(use="bathroom", length_m=2, width_m=2)["required"], 1)

    def test_the_count_chosen_by_the_person_still_wins(self):
        self.assertEqual(one(use="bedroom", length_m=2.5, width_m=3.2, count=4)["required"], 4)


class TestCorridor(unittest.TestCase):
    """Owner verdict 2026-11-10 (r4): the narrow-corridor rule only when the classification is stated."""

    def test_without_the_classification_the_corridor_follows_its_length(self):
        r = one(use="corridor", length_m=10, width_m=1.2)
        self.assertEqual((r["required"], r["basis"]), (2, "length"))                          # ceil(10 / 5)

    def test_a_wide_side_counts_as_the_length(self):
        self.assertEqual(one(use="corridor", length_m=1.2, width_m=10)["required"], 2)

    def test_with_the_classification_the_perimeter_rule_applies(self):
        r = one(use="corridor", length_m=10, width_m=1.2, narrow=True)
        self.assertEqual((r["required"], r["basis"]), (3, "perimeter"))                       # ceil(22.4 / 10)

    def test_narrow_false_is_the_same_as_not_stated(self):
        self.assertEqual(one(use="corridor", length_m=10, width_m=1.2, narrow=False)["required"], 2)

    def test_a_short_corridor_keeps_the_minimum_of_one(self):
        self.assertEqual(one(use="corridor", length_m=3, width_m=1)["required"], 1)

    def test_narrow_is_ignored_by_uses_without_that_rule(self):
        self.assertEqual(one(use="office", length_m=6, width_m=4, narrow=True)["required"], 3)

    def test_narrow_must_be_true_or_false(self):
        with self.assertRaises(ReceptaclesError):
            one(use="corridor", length_m=10, width_m=1.2, narrow="yes")


if __name__ == "__main__":
    unittest.main()
