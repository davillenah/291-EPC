"""Validation against pvlib on synthetic projects of 1 MWp to 500 MWp (target: every project within 0.02 % of the pvlib reference in annual energy; layouts identical).

`validation/reference.json` was written once by `validation/make_reference.py` with pvlib (a golden file: never edited by hand). The default run checks every 40th
project (25 projects); `EPC_PV_FULL=1` checks the 1000 projects of the owner's requirement (a few minutes).
"""
import json
import math
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "validation"))

import cases  # noqa: E402
from epc_pv import config, run  # noqa: E402

REFERENCE = json.loads((HERE / "validation" / "reference.json").read_text(encoding="utf-8"))
PROJECTS = 1000
TOLERANCE = 2e-4                                       # 0.02 %: the owner's 99.98 % match
FULL = os.environ.get("EPC_PV_FULL") == "1"
SELECTED = list(range(1, PROJECTS + 1)) if FULL else list(range(1, PROJECTS + 1, 40))


def rel(a: float, b: float) -> float:
    return abs(a / b - 1.0) if b else abs(a)


class TestAgainstPvlib(unittest.TestCase):
    def test_the_reference_covers_the_1000_projects(self):
        self.assertEqual(sorted(int(k) for k in REFERENCE["projects"]), list(range(1, PROJECTS + 1)))
        self.assertEqual(REFERENCE["model"], "haydavies")

    def test_projects_match_pvlib_and_the_layout_is_valid(self):
        worst = 0.0
        sizes = []
        for n in SELECTED:
            doc = cases.project(n)
            result = run(doc).as_dict()
            ref = REFERENCE["projects"][str(n)]["arrays"]
            self.assertEqual(len(result["arrays"]), len(ref), n)
            for got, want in zip(result["arrays"], ref):
                tag = f"project {n} array {got['id']}"
                self.assertEqual((got["modules"], got["inverters"], got["strings"]["n_series"]), (want["modules"], want["inverters"], want["n_series"]), tag)
                for key in ("ac_kwh", "dc_kwh", "poa_kwh_m2"):
                    err = rel(got[key], want[key])
                    worst = max(worst, err)
                    self.assertLessEqual(err, TOLERANCE, f"{tag} {key}")
                for month, (g, w) in enumerate(zip(got["monthly_ac_kwh"], want["monthly_ac_kwh"]), 1):
                    self.assertLessEqual(abs(g - w) / want["ac_kwh"], TOLERANCE, f"{tag} month {month}")
                self.check_layout(doc, got)
                sizes.append(got["dc_kwp"])
            self.assertLessEqual(rel(result["totals"]["ac_kwh"], sum(a["ac_kwh"] for a in ref)), TOLERANCE, f"project {n} total")
        self.assertGreater(max(sizes), 100000.0)               # large plants are in the set (kWp)
        print(f"\nvalidation: {len(SELECTED)} projects, {len(sizes)} arrays, worst annual error {worst * 100:.5f} % (limit {TOLERANCE * 100:.2f} %), largest array {max(sizes) / 1000:.0f} MWp")

    def check_layout(self, doc, got):
        """The layout satisfies the voltage and current limits with the numbers of the input (independent of the engine's own range)."""
        spec = next(a for a in doc["arrays"] if a["id"] == got["id"])
        mod, inv = spec["module"], spec["inverter"]
        s = got["strings"]["n_series"]
        beta = mod["beta_voc_pct_c"] / 100.0
        t_min = doc["site"]["design_t_min_c"]
        self.assertLessEqual(s * mod["voc_v"] * (1 + beta * (t_min - 25.0)), inv["vdc_max_v"] + 1e-9)
        self.assertLessEqual(s * mod["vmp_v"] * (1 + beta * (t_min - 25.0)), inv["mppt_v_max"] + 1e-9)
        self.assertGreaterEqual(got["modules"], spec["n_modules"])
        self.assertEqual(got["modules"] % s, 0)
        self.assertLess(got["modules"] - spec["n_modules"], s)
        self.assertGreaterEqual(got["inverters"], 1)
        if got["strings"]["strings_per_mppt"] <= got["strings"]["strings_per_mppt_limit"]:
            k = config.params()["strings"]["isc_factor"]
            self.assertLessEqual(got["strings"]["strings_per_mppt"] * mod["isc_a"] * k, inv["isc_max_input_a"] + 1e-9)

    def test_the_catalog_and_the_weather_are_reproducible(self):
        self.assertEqual(cases.project(7)["arrays"], cases.project(7)["arrays"])
        a, b = cases.project(3)["weather"], cases.project(3)["weather"]
        self.assertEqual(a["ghi"], b["ghi"])
        self.assertEqual(len(a["ghi"]), cases.YEAR_HOURS)
        self.assertFalse(math.isnan(sum(a["temp_air_c"])))


if __name__ == "__main__":
    unittest.main()
