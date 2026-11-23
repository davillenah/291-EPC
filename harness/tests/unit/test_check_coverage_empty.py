"""The incremental gate with no engine suite affected (a documentation change) runs no suite under coverage: the coverage check has no area to
check and passes, instead of failing on missing data. A run with areas, or without --areas (all of them), still needs the data."""
import importlib.util
import unittest
from pathlib import Path
from unittest import mock

SPEC = importlib.util.spec_from_file_location("check_coverage", Path(__file__).resolve().parents[2] / "tools" / "ci" / "check_coverage.py")
CC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CC)


class EmptyAreas(unittest.TestCase):
    def test_no_area_passes_without_reading_coverage(self):
        with mock.patch.object(CC, "combine", side_effect=AssertionError("must not read coverage")):
            self.assertEqual(CC.main(["--areas", ""]), 0)

    def test_areas_without_data_still_fail(self):
        with mock.patch.object(CC, "combine", return_value={}):
            self.assertEqual(CC.main(["--areas", "engine-pv"]), 1)
            self.assertEqual(CC.main([]), 1)


if __name__ == "__main__":
    unittest.main()
