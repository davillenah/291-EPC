"""Tests of harness/tools/build/validation_templates.py (MIG-42p): generated owner templates, ordering, empty owner columns, --check.

  python -m unittest harness/tools/build/tests/test_validation_templates.py
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "harness" / "tools" / "build"))
import validation_templates as V  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

OWNER_WS = [h for h, _ in V.OWNER]
VALUE_COLUMNS = re.compile(r"^(Valor|Tolerancia)")


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = V.N.Register(V.N.REPO)
        cls._holder = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._holder.name)
        V.write_all(cls.reg, cls.tmp)
        cls.ws_book = load_workbook(cls.tmp / V.WORKSHEET)
        cls.spike = load_workbook(cls.tmp / V.SPIKE)

    @classmethod
    def tearDownClass(cls):
        cls._holder.cleanup()

    def table(self, wb, sheet):
        rows = list(wb[sheet].iter_rows(values_only=True))
        return rows[0], rows[1:]


class Worksheet(Base):
    def test_row_count_equals_the_items_placed(self):
        items = V.collect_items(self.reg)
        _, rows = self.table(self.ws_book, V.SHEET_VERIF)
        self.assertEqual(len(rows), len({i["id"] for i in items}))
        self.assertEqual(len(rows), len(self.reg.records) + len(self.reg.auto))

    def test_groups_are_non_decreasing_and_ids_unique(self):
        head, rows = self.table(self.ws_book, V.SHEET_VERIF)
        order = [V.GROUPS.index(r[head.index("Grupo")]) for r in rows]
        self.assertEqual(order, sorted(order))
        ids = [r[head.index("Id del registro")] for r in rows]
        self.assertEqual(len(ids), len(set(ids)))

    def test_prefilled_values_equal_the_register(self):
        head, rows = self.table(self.ws_book, V.SHEET_VERIF)
        by_id = {r[head.index("Id del registro")]: r for r in rows}
        clause_i, eng_i, unit_i = head.index("Cláusula"), head.index("Motor/paquete"), head.index("Unidad")
        picked = [rec for _, rec in self.reg.records[::30]][:7] + self.reg.auto[::60][:4]
        self.assertGreaterEqual(len(picked), 10)
        for rec in picked:
            row = by_id[rec["id"]]
            self.assertEqual(row[clause_i], rec.get("clause") or V.NO_CLAUSE)
            self.assertTrue(row[eng_i])
        hand = self.reg.records[0][1]
        self.assertEqual(by_id[hand["id"]][unit_i], hand.get("unit") or None)

    def test_conflict_records_come_first_and_no_clause_second(self):
        head, rows = self.table(self.ws_book, V.SHEET_VERIF)
        conflicts = {r["id"] for _, r, i in self.reg.all_issues() if V.N.CONFLICT.match(i)}
        g = head.index("Grupo")
        first = {r[head.index("Id del registro")] for r in rows if r[g] == V.GROUPS[0]}
        self.assertEqual(first, conflicts)
        for r in rows:
            if r[head.index("Cláusula")] == V.NO_CLAUSE and r[head.index("Id del registro")] not in conflicts:
                self.assertEqual(r[g], V.GROUPS[1])

    def test_owner_columns_are_empty_in_the_worksheet(self):
        head, rows = self.table(self.ws_book, V.SHEET_VERIF)
        for name in OWNER_WS:
            self.assertEqual({r[head.index(name)] for r in rows}, {None}, name)

    def test_frozen_rows_are_flagged(self):
        head, rows = self.table(self.ws_book, V.SHEET_VERIF)
        flag = {r[head.index("Id del registro")]: r[head.index("Congelado")] for r in rows}
        self.assertEqual(flag["aea90364.criterion.raceway-fill-max-pct"], V.D15_TEXT)
        self.assertEqual(flag["plan.typical.occupancy.tray_pct"], V.D15_TEXT)
        self.assertEqual(flag["aea90364.code.aea_earthing.resistance_rod.simplificada"], V.D26_TEXT)
        self.assertIsNone(flag["aea90364.code.aea_earthing.resistance_rod.exacta"])

    def test_verdict_list_and_frozen_header(self):
        ws = self.ws_book[V.SHEET_VERIF]
        self.assertEqual(ws.freeze_panes, "D2")
        self.assertTrue(ws.auto_filter.ref.startswith("A1:"))
        lists = [(dv.formula1, str(dv.sqref)) for dv in ws.data_validations.dataValidation]
        col = V.COL["Veredicto"]
        self.assertEqual(lists, [('"Verificado,Corregir,Rechazar,Pendiente"', f"{col}2:{col}{ws.max_row}")])

    def test_summary_formulas_reference_the_right_ranges(self):
        n = self.ws_book[V.SHEET_VERIF].max_row - 1
        s = self.ws_book["Resumen"]
        verdict, group, ident = V.COL["Veredicto"], V.COL["Grupo"], V.COL["Id del registro"]
        self.assertEqual(s["B2"].value, f"=COUNTA('{V.SHEET_VERIF}'!${ident}$2:${ident}${n + 1})")
        self.assertIn(f"'{V.SHEET_VERIF}'!${group}$2:${group}${n + 1}", s["B5"].value)
        self.assertIn(f"'{V.SHEET_VERIF}'!${verdict}$2:${verdict}${n + 1}", s["C5"].value)
        self.assertEqual(s["C4"].value, "Verificado")
        total = 5 + len(V.GROUPS)
        self.assertEqual(s[f"A{total}"].value, "Total")
        self.assertTrue(s[f"D{total}"].value.startswith("=COUNTIF("))
        self.assertEqual(n, len(V.ordered_rows(self.reg)))


class Spike(Base):
    def test_sheets(self):
        self.assertEqual(self.spike.sheetnames, ["Instrucciones", "Perfil", "Áreas", "Cargas", "Requisitos", "Valores de referencia", "Tolerancias"])

    def test_profile_has_one_row_per_schema_field_and_empty_values(self):
        head, rows = self.table(self.spike, "Perfil")
        self.assertEqual(head[-1], "Valor")
        paths = [r[0] for r in rows]
        for p in ("project_code", "supply.earthing_system", "supply.short_circuit_level.value", "language"):
            self.assertIn(p, paths)
        self.assertEqual({r[-1] for r in rows}, {None})

    def test_loads_columns_and_lists(self):
        head, rows = self.table(self.spike, "Cargas")
        self.assertEqual(len(rows), V.BLANK_ROWS["Cargas"])
        self.assertTrue(all(all(c is None for c in r) for r in rows))
        lists = " ".join(dv.formula1 for dv in self.spike["Cargas"].data_validations.dataValidation)
        for token in ("lighting", "kVA", "1,3", "Áreas"):
            self.assertIn(token, lists)

    def test_reference_sheet_has_no_values(self):
        head, rows = self.table(self.spike, "Valores de referencia")
        self.assertEqual(head[4], "Valor de referencia (calculado de forma independiente)")
        names = {r[2] for r in rows}
        for n in ("Sección de fase", "Sección PE", "Corriente de diseño Ib", "Caída de tensión acumulada", "Corriente de cortocircuito mínima Icc mín"):
            self.assertIn(n, names)
        for r in rows:
            self.assertEqual(r[4:], (None, None, None, None))

    def test_no_numeric_cell_in_value_or_tolerance_columns(self):
        for ws in self.spike.worksheets:
            heads = {c.column: str(c.value) for c in ws[1] if c.value}
            for col, name in heads.items():
                if VALUE_COLUMNS.match(name) or "Tolerancia" in name:
                    for row in range(2, ws.max_row + 1):
                        self.assertIsNone(ws.cell(row=row, column=col).value, f"{ws.title}!{name}")
        tol = self.spike["Tolerancias"]
        self.assertEqual([c.value for c in tol["B"][1:]], [None] * (tol.max_row - 1))


class Check(Base):
    def test_check_passes_on_fresh_files(self):
        self.assertEqual(V.main(["--check", "--out", str(self.tmp)]), 0)

    def test_check_fails_when_a_prefilled_cell_is_edited(self):
        with tempfile.TemporaryDirectory() as name:
            copy = Path(name)
            V.write_all(self.reg, copy)
            wb = load_workbook(copy / V.WORKSHEET)
            wb[V.SHEET_VERIF]["G2"].value = "999"
            wb.save(copy / V.WORKSHEET)
            self.assertEqual(V.main(["--check", "--out", str(copy)]), 1)

    def test_check_fails_when_a_file_is_missing(self):
        with tempfile.TemporaryDirectory() as name:
            self.assertEqual(V.main(["--check", "--out", name]), 1)


if __name__ == "__main__":
    unittest.main()
