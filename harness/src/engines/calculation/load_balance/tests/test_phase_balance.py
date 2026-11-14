"""Phase balance: assignment of the single-phase circuits to R, S, T and the unbalance between the phases."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "calc_common" / "src"))

from epc_load_balance import aea_demand, phase_balance as PB   # noqa: E402


class ApparentPower(unittest.TestCase):
    def test_three_phase_and_single_phase(self):
        self.assertAlmostEqual(PB.apparent_kva(10, 400, 3), 6.9282, places=4)
        self.assertAlmostEqual(PB.apparent_kva(10, 400, 1), 2.3094, places=4)

    def test_a_missing_datum_gives_none(self):
        self.assertIsNone(PB.apparent_kva(None, 400, 1))
        self.assertIsNone(PB.apparent_kva(10, 0, 3))


class Assignment(unittest.TestCase):
    def test_a_three_phase_circuit_is_a_third_on_each_phase(self):
        self.assertEqual(PB.assign_phases([("M", 9.0, 3, "")]), {"M": [3.0, 3.0, 3.0]})

    def test_the_assigned_phase_is_kept(self):
        self.assertEqual(PB.assign_phases([("A", 4.0, 1, "S")])["A"], [0.0, 4.0, 0.0])

    def test_the_rest_go_biggest_first_on_the_least_loaded_phase(self):
        got = PB.assign_phases([("a", 1.0, 1, ""), ("b", 3.0, 1, ""), ("c", 2.0, 1, ""), ("d", 3.0, 1, "")])
        self.assertEqual(got["b"], [3.0, 0.0, 0.0])
        self.assertEqual(got["d"], [0.0, 3.0, 0.0])
        self.assertEqual(got["c"], [0.0, 0.0, 2.0])
        self.assertEqual(got["a"], [0.0, 0.0, 1.0])

    def test_it_is_deterministic(self):
        rows = [("x", 2.0, 1, ""), ("y", 2.0, 1, ""), ("z", 2.0, 1, "")]
        self.assertEqual(PB.assign_phases(rows), PB.assign_phases(list(reversed(rows))))


class Balance(unittest.TestCase):
    def test_totals_unbalance_and_the_limit_of_the_engine(self):
        r = PB.balance([("a", 3.0, 1, ""), ("b", 3.0, 1, ""), ("c", 3.0, 1, "")])
        self.assertEqual(r["totals"], [3.0, 3.0, 3.0])
        self.assertEqual((r["unbalance_pct"], r["complies"]), (0.0, True))
        self.assertEqual(r["limit_pct"], aea_demand.DESEQUILIBRIO_MAX_PCT)

    def test_an_uneven_board_does_not_comply(self):
        r = PB.balance([("a", 9.0, 1, "R"), ("b", 1.0, 1, "S"), ("c", 1.0, 1, "T")])
        self.assertFalse(r["complies"])
        self.assertGreater(r["unbalance_pct"], r["limit_pct"])


if __name__ == "__main__":
    unittest.main()
