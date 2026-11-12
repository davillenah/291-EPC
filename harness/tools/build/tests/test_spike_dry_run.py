"""Tests of harness/tools/build/spike_dry_run.py (MIG-44p): ten criteria, valid statuses, no invented reference values, report freshness, computed numbers.

  python -m pytest harness/tools/build/tests/test_spike_dry_run.py     (engines and harness/src on PYTHONPATH, as in the gate; the dry run takes about half a minute)

The statuses themselves (pass, partial, fail...) are NOT asserted here: they are measurements, and a gap that gets closed must change the report, not break a test.
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "harness" / "tools" / "build"))
import spike_dry_run as D  # noqa: E402

NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = D.evaluate()
        cls.text = D.render(cls.results)
        cls._holder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._holder.cleanup)
        cls.path = Path(cls._holder.name) / "SPIKE_DRY_RUN.md"


class Evaluation(Base):
    def test_exactly_ten_criteria_with_valid_statuses(self):
        self.assertEqual([r["criterion"] for r in self.results], list(range(1, 11)))
        for r in self.results:
            self.assertIn(r["status"], D.STATUSES)
            self.assertEqual(sorted(r), ["criterion", "evidence", "facts", "gaps", "status", "title"])
            self.assertTrue(r["title"] and r["evidence"], r["criterion"])

    def test_criteria_2_and_4_wait_for_the_owner_and_hold_no_reference_value(self):
        for number in (2, 4):
            r = self.results[number - 1]
            self.assertEqual(r["status"], "needs_owner_values")
            self.assertEqual(r["facts"]["owner_cells_filled"], 0)
            text = " ".join(r["evidence"] + r["gaps"])
            self.assertIsNone(re.search(r"\d+[.,]\d+", text), text)            # no decimal quantity, so no reference value or tolerance
            self.assertTrue(all(isinstance(v, int) for v in r["facts"].values()))

    def test_each_criterion_executed_something_measurable(self):
        for r in self.results:
            if r["criterion"] != 9:
                self.assertTrue(r["facts"], r["criterion"])
        self.assertEqual(self.results[9]["facts"]["stages_total"], 16)

    def test_criterion_5_compares_two_runs_with_the_drawing_date_pinned_and_notes_the_unpinned_behaviour(self):
        facts = self.results[4]["facts"]
        self.assertEqual(facts["files_differ"], 0)                          # pinned: every file, the DXF and the workbook included, is identical
        self.assertEqual(facts["files_identical"], facts["files"])
        self.assertEqual(facts["deliverables_identical"], facts["deliverables"])
        self.assertEqual(facts["unpinned_differ_unexplained"], 0)           # unpinned: only the stamped files and the hashes that embed them differ
        self.assertGreater(facts["unpinned_differ_stamped"], 0)
        self.assertIn("sin fijar la fecha", " ".join(self.results[4]["evidence"]))

    def test_a_crashing_check_becomes_a_fail_result(self):
        out = D.guarded(1, lambda run: 1 / 0, None)
        self.assertEqual(out["status"], "fail")
        self.assertIn("ZeroDivisionError", " ".join(out["gaps"]))


class Report(Base):
    def test_header_says_generated_and_synthetic(self):
        head = self.text.split("## Resumen")[0]
        self.assertIn("GENERADO", head)
        self.assertIn("SINTÉTICOS", head)
        self.assertIn("NO es el spike", head)

    def test_every_criterion_is_in_the_table(self):
        for r in self.results:
            self.assertIn(f"| C{r['criterion']}. ", self.text)

    def test_fresh_output_passes_check_and_an_edited_file_fails(self):
        self.assertEqual(D.main(["--out", str(self.path)], results=self.results), 0)
        self.assertEqual(self.path.read_text(encoding="utf-8"), self.text)
        self.assertEqual(D.main(["--check", "--out", str(self.path)], results=self.results), 0)
        self.path.write_text(self.text + "edited\n", encoding="utf-8", newline="\n")
        self.assertEqual(D.main(["--check", "--out", str(self.path)], results=self.results), 1)
        self.assertEqual(D.main(["--check", "--out", str(self.path.with_name("missing.md"))], results=self.results), 1)

    def test_numbers_in_the_report_are_the_computed_facts(self):
        """No digits are typed in the report except identifiers (criterion ids C1.., MIG-xx, PRD section numbers, R0/R1, T-01...) and values computed from the run."""
        allowed = {str(v) for r in self.results for v in r["facts"].values()}
        allowed |= {str(len(self.results))} | {str(sum(1 for r in self.results if r["status"] == s)) for s in D.STATUSES}
        body = re.sub(D.IDENTIFIER_PATTERN, " ", self.text)
        stray = sorted({n for n in NUMBER.findall(body) if n not in allowed})
        self.assertEqual(stray, [])

    def test_the_source_types_no_digit_literal_in_the_report_texts(self):
        """The Spanish evidence and gap strings of the script carry digits only inside f-string placeholders or identifiers."""
        source = (REPO / "harness" / "tools" / "build" / "spike_dry_run.py").read_text(encoding="utf-8")
        texts = re.findall(r'f?"(?:[^"\\]|\\.)*[áéíóúñ](?:[^"\\]|\\.)*"', source)
        self.assertTrue(texts)
        for text in texts:
            plain = re.sub(r"\{[^{}]*\}", " ", text)
            plain = re.sub(D.IDENTIFIER_PATTERN, " ", plain)
            self.assertIsNone(NUMBER.search(plain), text)


if __name__ == "__main__":
    unittest.main()
