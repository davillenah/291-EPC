"""Hand-checked quick selects."""
import unittest

from epc_select import SelectError, select
from epc_select import api  # noqa: F401  (the public door imports)

R = [
    {"id": "C1", "kind": "lighting", "section": 1.5, "tags": ["a", "b"], "note": "main hall"},
    {"id": "C2", "kind": "motor", "section": 6, "tags": ["b"], "note": "pump"},
    {"id": "C3", "kind": "lighting", "section": 2.5, "tags": []},
    {"id": "C4", "kind": "socket", "section": "x", "flag": True},
]


def go(conds, match="all", records=R, limit=100):
    return select(records, conds, match=match, max_results=limit)


def ids(answer):
    return [r["id"] for r in answer["matches"]]


class Select(unittest.TestCase):
    def test_equal_and_different(self):
        self.assertEqual(ids(go([{"field": "kind", "op": "eq", "value": "lighting"}])), ["C1", "C3"])
        self.assertEqual(ids(go([{"field": "kind", "op": "ne", "value": "lighting"}])), ["C2", "C4"])
        self.assertEqual(ids(go([{"field": "flag", "op": "ne", "value": True}])), ["C1", "C2", "C3"])   # absent is different

    def test_ordered_comparisons_only_meet_numbers_with_numbers_and_texts_with_texts(self):
        self.assertEqual(ids(go([{"field": "section", "op": "ge", "value": 2.5}])), ["C2", "C3"])
        self.assertEqual(ids(go([{"field": "section", "op": "lt", "value": 2.5}])), ["C1"])
        self.assertEqual(ids(go([{"field": "section", "op": "gt", "value": "a"}])), ["C4"])
        self.assertEqual(ids(go([{"field": "flag", "op": "gt", "value": 0}])), [])          # a boolean is not a number
        self.assertEqual(ids(go([{"field": "section", "op": "le", "value": 1.5}])), ["C1"])

    def test_in_contains_and_exists(self):
        self.assertEqual(ids(go([{"field": "kind", "op": "in", "value": ["motor", "socket"]}])), ["C2", "C4"])
        self.assertEqual(ids(go([{"field": "note", "op": "contains", "value": "hall"}])), ["C1"])
        self.assertEqual(ids(go([{"field": "tags", "op": "contains", "value": "b"}])), ["C1", "C2"])
        self.assertEqual(ids(go([{"field": "section", "op": "contains", "value": "b"}])), [])
        self.assertEqual(ids(go([{"field": "note", "op": "contains", "value": 1}])), [])
        self.assertEqual(ids(go([{"field": "note", "op": "exists"}])), ["C1", "C2"])
        self.assertEqual(ids(go([{"field": "note", "op": "exists", "value": False}])), ["C3", "C4"])

    def test_all_and_any(self):
        both = [{"field": "kind", "op": "eq", "value": "lighting"}, {"field": "section", "op": "gt", "value": 2}]
        self.assertEqual(ids(go(both)), ["C3"])
        self.assertEqual(ids(go(both, "any")), ["C1", "C2", "C3"])
        self.assertEqual(ids(go([])), ["C1", "C2", "C3", "C4"])
        self.assertEqual(ids(go([], "any")), [])

    def test_indices_count_and_determinism(self):
        a = go([{"field": "kind", "op": "eq", "value": "lighting"}])
        self.assertEqual((a["indices"], a["count"]), ([0, 2], 2))
        self.assertEqual(a, go([{"field": "kind", "op": "eq", "value": "lighting"}]))


class Refusals(unittest.TestCase):
    def code(self, *a, **kw):
        with self.assertRaises(SelectError) as c:
            go(*a, **kw)
        self.assertTrue(c.exception.es)
        return c.exception.code

    def test_bad_input(self):
        self.assertEqual(self.code([], records="x"), "err_not_records")
        self.assertEqual(self.code([], records=[1]), "err_not_records")
        self.assertEqual(self.code([], match="some"), "err_bad_match")
        self.assertEqual(self.code([], limit=0), "err_not_count")
        self.assertEqual(self.code([], limit=True), "err_not_count")
        self.assertEqual(self.code(["x"]), "err_bad_condition")
        self.assertEqual(self.code([{"field": "", "op": "eq", "value": 1}]), "err_bad_condition")
        self.assertEqual(self.code([{"field": "a"}]), "err_bad_condition")
        self.assertEqual(self.code([{"field": "a", "op": "eq"}]), "err_bad_condition")
        self.assertEqual(self.code([{"field": "a", "op": "in", "value": 3}]), "err_bad_condition")
        self.assertEqual(self.code([{"field": "a", "op": "like", "value": 3}]), "err_unknown_op")

    def test_too_many(self):
        self.assertEqual(self.code([], limit=2), "err_too_many")


if __name__ == "__main__":
    unittest.main()
