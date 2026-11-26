"""Energy over the life of the plant from a degradation the document gives (no default)."""
import unittest

from epc_pv import PvError, lifetime, run

from test_pv import doc


class TestLifetime(unittest.TestCase):
    def test_year_one_is_the_run_and_each_year_keeps_a_share(self):
        out = lifetime.project(1000.0, {"pct_per_year": 0.5, "years": 4})
        self.assertEqual(out, [1000.0, 995.0, 990.025, 985.075])

    def test_zero_degradation_is_flat(self):
        self.assertEqual(lifetime.project(10.0, {"pct_per_year": 0.0, "years": 3}), [10.0] * 3)

    def test_without_the_block_nothing_is_added(self):
        r = run(doc()).as_dict()
        self.assertNotIn("lifetime_ac_kwh", r["totals"])
        self.assertNotIn("lifetime_ac_kwh", r["arrays"][0])

    def test_with_the_block_every_array_and_the_total_carry_the_years(self):
        d = doc()
        d["assumptions"] = {"degradation": {"pct_per_year": 0.4, "years": 25}}
        r = run(d).as_dict()
        self.assertEqual(len(r["arrays"][0]["lifetime_ac_kwh"]), 25)
        self.assertEqual(r["arrays"][0]["lifetime_ac_kwh"][0], r["arrays"][0]["ac_kwh"])
        self.assertAlmostEqual(r["totals"]["lifetime_total_ac_kwh"], sum(r["totals"]["lifetime_ac_kwh"]), places=2)
        self.assertLess(r["totals"]["lifetime_ac_kwh"][-1], r["totals"]["lifetime_ac_kwh"][0])

    def test_bad_blocks_are_errors_in_both_languages(self):
        for bad in ("x", {"years": 5}, {"pct_per_year": 0.5}, {"pct_per_year": 120, "years": 5}, {"pct_per_year": 0.5, "years": 0}, {"pct_per_year": "a", "years": 5}):
            with self.assertRaises(PvError) as ctx:
                lifetime.parse({"degradation": bad})
            self.assertTrue(ctx.exception.en and ctx.exception.es)


if __name__ == "__main__":
    unittest.main()
