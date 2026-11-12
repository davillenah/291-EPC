"""MIG-38b: `disciplines.electrical_lv.norm_review`, the read-only review units that replaced the parked norms page for the harness."""
import json
import tempfile
import unittest
from pathlib import Path

from disciplines.electrical_lv import norm_review as nr


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def synthetic(root, review=None):
    rule = {"id": "R1", "tema": "t", "fuente": {"norma": "AEA 1", "edicion": "2006", "clausula": "1.1", "pagina_impresa": 3}}
    write(root / "rules" / "a.json", {"reglas": [rule, dict(rule, id="R2")]})
    write(root / "rules" / "_skip.json", {"reglas": [dict(rule, id="X")]})
    write(root / "tables.json", {"tablas_capacidad": {"T1": {"titulo": "x"}}, "factores_correccion": {"F1": 0.8}, "constantes": {"K": 1}})
    write(root / "criteria.json", {"criteria": [{"id": "c1"}, {"id": "c2"}]})
    write(root / "lighting" / "n.rules.json", {"norm": "N 1", "rules": [{"id": "L1", "review": "x", "value": 100}]})
    write(root / "typical.json", {"sizing": {"a": 1, "note": "n"}, "params": {"note": 2}})
    write(root / "review.json", {"points": review or {}})
    return {"plan": root / "typical.json", "receptacles": root / "missing.json", "hvac": root / "typical.json", "rules": root / "rules", "tables": root / "tables.json",
            "criteria": root / "criteria.json", "review": root / "review.json", "lighting": root / "lighting"}


class Units(unittest.TestCase):
    def counts(self, review=None):
        with tempfile.TemporaryDirectory() as tmp:
            return {u["id"]: u["counts"] for u in nr.units(synthetic(Path(tmp), review))}

    def test_every_point_is_pending_without_a_review_file_record(self):
        counts = self.counts()
        self.assertEqual(counts["rule:aea-1-2006"], {"total": 2, "approved": 0, "rejected": 0, "pending": 2, "stale": 0})
        self.assertEqual(counts["table:aea-calculo"]["total"], 3)
        self.assertEqual(counts["criterion:ar-electrical"]["total"], 2)
        self.assertEqual(counts["lighting-rule:n-1"]["total"], 1)
        self.assertEqual(counts["table:plan-valores-tipicos"]["total"], 1)          # the note is not a point
        self.assertEqual(counts["table:hvac-valores-tipicos"]["total"], 1)          # hvac keeps its keys
        self.assertNotIn("table:receptacles-valores-tipicos", counts)               # no file, no unit

    def test_the_status_rule(self):
        rule = {"id": "R1", "tema": "t", "fuente": {"norma": "AEA 1", "edicion": "2006", "clausula": "1.1", "pagina_impresa": 3}}
        review = {"rule:aea-1-2006|R1": {"status": "approved", "sha": nr.fingerprint(rule)},
                  "rule:aea-1-2006|R2": {"status": "approved", "sha": "old"},
                  "criterion:ar-electrical|c1": {"status": "rejected"}}
        counts = self.counts(review)
        self.assertEqual(counts["rule:aea-1-2006"], {"total": 2, "approved": 1, "rejected": 0, "pending": 0, "stale": 1})
        self.assertEqual(counts["criterion:ar-electrical"]["rejected"], 1)

    def test_summary_counts_stale_as_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = synthetic(Path(tmp), {"rule:aea-1-2006|R2": {"status": "approved", "sha": "old"}})
            total = nr.summary(src)
        self.assertEqual(total["pending_points"], sum(r["pending"] for r in total["rows"]))
        self.assertEqual(total["units"], len(total["rows"]))

    def test_reading_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = synthetic(Path(tmp))
            before = {p: p.read_bytes() for p in Path(tmp).rglob("*") if p.is_file()}
            nr.units(src)
            self.assertEqual({p: p.read_bytes() for p in Path(tmp).rglob("*") if p.is_file()}, before)

    def test_the_real_engines_give_the_fifteen_units_and_a_pending_total(self):
        found = nr.units()
        self.assertEqual(len(found), 15)
        self.assertTrue(all(sum(u["counts"][s] for s in nr.STATUSES) == u["counts"]["total"] for u in found))
        self.assertGreater(nr.summary()["pending_points"], 0)


if __name__ == "__main__":
    unittest.main()
