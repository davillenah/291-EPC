"""Hand-checked change summaries between two revisions."""
import unittest

from epc_changes import ChangesError, compare
from epc_changes import api  # noqa: F401  (the public door imports)

A = [{"id": "C1", "section": 2.5, "breaker": 16, "rev": "A"}, {"id": "C2", "section": 4, "breaker": 20, "rev": "A"}, {"id": "C3", "section": 6, "breaker": 25, "rev": "A"}]
B = [{"id": "C1", "section": 2.5, "breaker": 16, "rev": "B"}, {"id": "C2", "section": 6, "breaker": 25, "rev": "B"}, {"id": "C4", "section": 1.5, "breaker": 10, "rev": "B"}]


def go(prev, cur, **kw):
    args = dict(id_field="id", ignore=[], max_changes=100)
    args.update(kw)
    return compare(prev, cur, **args)


class Compare(unittest.TestCase):
    def test_added_removed_and_changed(self):
        r = go(A, B, ignore=["rev"])
        self.assertEqual([x["id"] for x in r["added"]], ["C4"])
        self.assertEqual([x["id"] for x in r["removed"]], ["C3"])
        self.assertEqual(r["changed"], [{"id": "C2", "fields": [{"field": "breaker", "before": 20, "after": 25}, {"field": "section", "before": 4, "after": 6}]}])
        self.assertEqual(r["summary"], {"added": 1, "removed": 1, "changed": 1, "unchanged": 1})

    def test_an_ignored_field_does_not_count_and_a_counted_one_does(self):
        self.assertEqual(go(A, B, ignore=["rev"])["summary"]["changed"], 1)
        self.assertEqual(go(A, B)["summary"]["changed"], 2)       # C1 changes only in `rev`

    def test_a_field_on_one_side_only_is_marked(self):
        r = go([{"id": 1, "a": 1}], [{"id": 1, "a": 1, "b": 2}])
        self.assertEqual(r["changed"][0]["fields"], [{"field": "b", "before": None, "after": 2, "present": "after"}])
        r = go([{"id": 1, "a": 1, "b": 2}], [{"id": 1, "a": 1}])
        self.assertEqual(r["changed"][0]["fields"], [{"field": "b", "before": 2, "after": None, "present": "before"}])

    def test_nested_values_compare_whole_and_order_of_records_does_not_matter(self):
        r = go([{"id": "x", "v": {"k": [1, 2]}}, {"id": "y", "v": 0}], [{"id": "y", "v": 0}, {"id": "x", "v": {"k": [1, 2]}}])
        self.assertEqual(r["summary"], {"added": 0, "removed": 0, "changed": 0, "unchanged": 2})
        r = go([{"id": "x", "v": {"k": [1, 2]}}], [{"id": "x", "v": {"k": [1, 3]}}])
        self.assertEqual(r["changed"][0]["fields"][0]["after"], {"k": [1, 3]})

    def test_identical_revisions_have_no_changes(self):
        self.assertEqual(go(A, A)["summary"], {"added": 0, "removed": 0, "changed": 0, "unchanged": 3})

    def test_the_same_input_gives_the_same_answer(self):
        self.assertEqual(go(A, B), go(A, B))


class Refusals(unittest.TestCase):
    def code(self, *a, **kw):
        with self.assertRaises(ChangesError) as c:
            go(*a, **kw)
        self.assertTrue(c.exception.es)
        return c.exception.code

    def test_bad_records(self):
        self.assertEqual(self.code("x", []), "err_not_records")
        self.assertEqual(self.code([], {"id": 1}), "err_not_records")
        self.assertEqual(self.code([{"name": "a"}], []), "err_missing_id")
        self.assertEqual(self.code([5], []), "err_missing_id")
        self.assertEqual(self.code([{"id": True}], []), "err_missing_id")
        self.assertEqual(self.code([{"id": ""}], []), "err_missing_id")
        self.assertEqual(self.code([], [{"id": 1}, {"id": 1}]), "err_duplicate_id")

    def test_bad_arguments(self):
        self.assertEqual(self.code([], [], id_field=""), "err_not_text")
        self.assertEqual(self.code([], [], ignore="rev"), "err_not_names")
        self.assertEqual(self.code([], [], ignore=[""]), "err_not_names")
        self.assertEqual(self.code([], [], max_changes=0), "err_not_count")
        self.assertEqual(self.code([], [], max_changes=True), "err_not_count")

    def test_too_many_changes(self):
        self.assertEqual(self.code([], [{"id": 1}, {"id": 2}], max_changes=1), "err_too_many")


if __name__ == "__main__":
    unittest.main()
