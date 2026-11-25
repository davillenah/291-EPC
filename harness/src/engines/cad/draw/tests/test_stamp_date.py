"""MIG-3Z: the title block service takes the date of the drawing (`today`) and, for the DXF, an optional stamp date; the defaults are unchanged."""
import datetime
import sys
import tempfile
import unittest
from pathlib import Path

ENGINES = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ENGINES / "cad" / a / "src") for a in ("titleblock", "dxf", "symbols")]

from epc_draw.titleblock import service  # noqa: E402


def sheets_result():
    request = service.project_request({"company": "ACME", "client": "CLIENTE", "drawn_by": "D. Proyecta"}, None, datetime.date(2026, 3, 4))
    request["sheets"] = [{"name": "SLD_T1", "format": "A3", "fields": {"denominacion": "TGBT-01", "proyecto": "PRJ-1"}}]
    return service.render(request)


class TestToday(unittest.TestCase):
    def test_the_three_dates_are_the_given_day(self):
        common = service.project_request({}, None, datetime.date(2026, 3, 4))["common"]
        self.assertEqual((common["proy_fecha"], common["ver_fecha"], common["val_fecha"]), ("04/03/2026",) * 3)

    def test_without_a_day_it_is_today(self):
        common = service.project_request({})["common"]
        self.assertEqual(common["proy_fecha"], datetime.date.today().strftime("%d/%m/%Y"))


class TestWriteWithStamp(unittest.TestCase):
    def test_the_dxf_is_reproducible_with_a_stamp_date(self):
        with tempfile.TemporaryDirectory() as t:
            dxfs = []
            for i in range(2):
                files = service.write(sheets_result(), Path(t, f"run{i}"), True, stamp_date="2026-03-04")
                dxfs.append(next(f for f in files if f.suffix == ".dxf").read_bytes())
            self.assertEqual(dxfs[0], dxfs[1])
            self.assertIn(b"04/03/2026", Path(t, "run0", "SLD_T1.svg").read_bytes())

    def test_without_a_stamp_date_the_dxf_is_stamped_by_the_clock(self):
        with tempfile.TemporaryDirectory() as t:
            dxfs = [next(f for f in service.write(sheets_result(), Path(t, f"run{i}"), True) if f.suffix == ".dxf").read_bytes() for i in range(2)]
            self.assertNotEqual(dxfs[0], dxfs[1])


if __name__ == "__main__":
    unittest.main()
