"""MIG-3Z: `design(..., drawing_date=...)` pins every date, time and GUID, so the same inputs give byte-identical files; without it nothing is pinned."""
import datetime
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import openpyxl

from epc_drawing import board_design as B

DATA = {"board": {"name": "TGBT-01", "voltage_v": 380, "system": "TN-S", "icc_ka": 25, "fp_default": 0.85, "frequency_hz": 50, "project": "P", "feeder_length_m": 20},
        "circuits": [{"tag": "C-01", "description": "ALIMENTADOR", "load": 100, "unit": "A", "topology": "single", "phase": "3F", "length_m": 60, "kind": "mccb"},
                     {"tag": "M-01", "description": "BOMBA", "load": 15, "unit": "kW", "topology": "dol_ol", "phase": "3F", "length_m": 80, "fp": 0.85, "efficiency": 0.9}],
        "titleblock": {"company": "ACME", "client": "CLIENTE", "drawn_by": "D. Proyecta"}}
DAY = "2026-03-04"


def files_of(folder):
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(Path(folder).rglob("*")) if p.is_file()}


def design(folder, drawing_date=None, diagrams=("sld",)):
    summary = B.design(json.loads(json.dumps(DATA)), Path(folder), "T1", None, None, 18, diagrams, drawing_date)
    assert summary["ok"], summary["error"]
    return summary


class TestDrawingDay(unittest.TestCase):
    def test_text_date_and_datetime_give_the_day(self):
        expected = datetime.date(2026, 3, 4)
        for value in (DAY, f"{DAY}T10:30:00", expected, datetime.datetime(2026, 3, 4, 23, 59)):
            self.assertEqual(B.drawing_day(value), expected, value)

    def test_none_is_none_and_anything_else_is_an_error(self):
        self.assertIsNone(B.drawing_day(None))
        for bad in ("04/03/2026", "not a date", 20260304):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                B.drawing_day(bad)


class TestWorkbook(unittest.TestCase):
    rows = ({"NOMBRE": "T1", "TENSION_V": 380}, [{"TAG": "C-01", "CARGA": 10}])

    def test_with_a_date_two_workbooks_are_byte_identical_and_carry_the_date(self):
        with tempfile.TemporaryDirectory() as t:
            first, second = Path(t, "a.xlsx"), Path(t, "b.xlsx")
            B.write_excel(first, *self.rows, DAY)
            B.write_excel(second, *self.rows, DAY)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as z:
                self.assertEqual({info.date_time for info in z.infolist()}, {(2026, 3, 4, 0, 0, 0)})
            wb = openpyxl.load_workbook(first)
            self.assertEqual((wb.properties.created, wb.properties.modified), (datetime.datetime(2026, 3, 4), datetime.datetime(2026, 3, 4)))
            self.assertEqual([ws.title for ws in wb], ["TABLERO", "CIRCUITOS"])
            self.assertEqual(wb["CIRCUITOS"]["A3"].value, "C-01")

    def test_without_a_date_the_workbook_is_the_openpyxl_default(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t, "a.xlsx")
            B.write_excel(path, *self.rows)
            modified = openpyxl.load_workbook(path).properties.modified
            self.assertLess(abs(datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None) - modified), datetime.timedelta(minutes=5))


class TestDesign(unittest.TestCase):
    def test_the_same_inputs_and_date_give_identical_files(self):
        with tempfile.TemporaryDirectory() as t:
            design(Path(t, "one"), DAY, ("sld", "mld"))
            design(Path(t, "two"), DAY, ("sld", "mld"))
            one, two = files_of(Path(t, "one")), files_of(Path(t, "two"))
            self.assertEqual(sorted(one), sorted(two))
            self.assertTrue(any(name.endswith(".dxf") for name in one))
            self.assertTrue(any("MLD_" in name and name.endswith(".dxf") for name in one))
            self.assertIn("input_for_sld.xlsx", one)
            self.assertEqual([name for name in one if one[name] != two[name]], [])

    def test_the_date_reaches_the_title_block_and_the_sheets(self):
        with tempfile.TemporaryDirectory() as t:
            design(Path(t), DAY)
            request = json.loads(Path(t, "titleblock-request.json").read_text(encoding="utf-8"))
            self.assertEqual({request["common"][k] for k in ("proy_fecha", "ver_fecha", "val_fecha")}, {"04/03/2026"})
            svg = next(Path(t, "out").glob("SLD_T1*.svg")).read_text(encoding="utf-8")
            self.assertIn("04/03/2026", svg)

    def test_another_date_gives_another_drawing(self):
        with tempfile.TemporaryDirectory() as t:
            design(Path(t, "one"), DAY)
            design(Path(t, "two"), "2026-03-05")
            one, two = files_of(Path(t, "one")), files_of(Path(t, "two"))
            self.assertNotEqual(one["out/SLD_T1.dxf"], two["out/SLD_T1.dxf"])
            self.assertEqual(one["out/T1_dimensionado.json"], two["out/T1_dimensionado.json"])        # the numbers do not depend on the date

    def test_without_a_date_nothing_is_pinned(self):
        with tempfile.TemporaryDirectory() as t:
            design(Path(t, "one"))
            design(Path(t, "two"))
            one, two = files_of(Path(t, "one")), files_of(Path(t, "two"))
            self.assertNotEqual(one["out/SLD_T1.dxf"], two["out/SLD_T1.dxf"])                      # the clock and random GUIDs, as before
            request = json.loads(Path(t, "one", "titleblock-request.json").read_text(encoding="utf-8"))
            self.assertEqual(request["common"]["proy_fecha"], datetime.date.today().strftime("%d/%m/%Y"))

    def test_an_invalid_date_is_refused_before_anything_is_written(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):
                B.design(json.loads(json.dumps(DATA)), Path(t), "T1", None, None, 18, ("sld",), "tomorrow")
            self.assertEqual(list(Path(t).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
