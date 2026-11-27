import unittest

from epc_report.core import audit as a

GOOD = {"title": "A", "facts": {"pv.dc_kwp": 10.0}, "blocks": [{"type": "h", "text": "S"}, {"type": "p", "text": "ok"}]}
BAD = {"title": "B", "blocks": []}


class TestAudit(unittest.TestCase):
    def test_clean_set(self):
        self.assertEqual(a.audit([GOOD]), [])

    def test_findings(self):
        bad = {"title": "B", "facts": {"pv.dc_kwp": 11.0}, "blocks": [{"type": "h", "text": "S"}, {"type": "table", "columns": [["a", 1.0]], "rows": [["x", "y"]]}, {"type": "p", "text": "[DEFINIR]"}]}
        codes = {f["code"] for f in a.audit([GOOD, bad])}
        self.assertTrue({"row_width", "placeholder", "fact_mismatch"} <= codes)

    def test_loop_stops_at_five_and_at_no_change(self):
        calls = []

        def grow(reps, fs):
            calls.append(1)
            return [dict(r, n=len(calls)) for r in reps]
        out = a.audit_loop([BAD], grow, max_iterations=99)
        self.assertEqual(out["iterations"], 5)
        self.assertFalse(out["clean"])
        self.assertEqual(a.audit_loop([BAD], lambda r, f: r)["iterations"], 1)

    def test_loop_fixes(self):
        out = a.audit_loop([BAD], lambda r, f: [dict(x, blocks=[{"type": "p", "text": "ok"}]) for x in r])
        self.assertTrue(out["clean"])
        self.assertEqual(out["iterations"], 1)

    def test_same_input_same_output(self):
        self.assertEqual(a.audit([GOOD]), a.audit([GOOD]))

    def test_structure_findings(self):
        rep = {"blocks": [{"type": "h", "text": ""}, {"type": "h", "text": "S"}, {"type": "h", "text": "S"},
                          {"type": "table", "columns": [["a", 1.0]], "rows": []}, {"type": "p", "text": "None"}, {"type": "p", "text": "nan"}]}
        codes = [f["code"] for f in a.audit([rep])]
        for c in ("missing_title", "empty_heading", "duplicate_heading", "empty_section", "empty_table", "bad_value"):
            self.assertIn(c, codes)
        self.assertEqual(a.audit([{"title": "T", "blocks": [{"type": "h", "text": "S"}]}])[0]["code"], "empty_section")

    def test_fact_values_and_text(self):
        r1 = {"title": "A", "blocks": [{"type": "p", "text": "x"}], "facts": {"k": "a", "n": 1.0}}
        r2 = {"title": "B", "blocks": [{"type": "p", "text": "x"}], "facts": {"k": "b", "n": 1.0}}
        self.assertEqual([f["code"] for f in a.audit([r1, r2])], ["fact_mismatch"])
        self.assertEqual(a._texts({"type": "bullets", "items": ["i"]}), ["i"])


if __name__ == "__main__":
    unittest.main()


class TestReviewRound(unittest.TestCase):
    def test_owner_edit_is_reviewed_again(self):
        fix = lambda r, f: [dict(x, blocks=[{"type": "p", "text": "ok"}]) for x in r]  # noqa: E731
        first = a.review_round([BAD], fix)
        self.assertEqual(first["status"], "ready_for_owner")
        second = a.review_round(first["reports"], fix, owner_edit=lambda r: [dict(x, blocks=[]) for x in r])
        self.assertEqual((second["status"], second["iterations"]), ("ready_for_owner", 1))

    def test_not_clean_after_five(self):
        out = a.review_round([BAD], lambda r, f: [dict(x, n=x.get("n", 0) + 1) for x in r])
        self.assertEqual((out["status"], out["iterations"]), ("needs_work", 5))
