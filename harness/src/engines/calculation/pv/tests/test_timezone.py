"""Time zone of a place: the standard offset, never the summer one; nothing when the place has no zone or the database is missing."""
import sys
import unittest
from unittest import mock

from epc_pv import timezone


class TestTimezone(unittest.TestCase):
    def test_the_standard_offset_of_a_place(self):
        self.assertEqual(timezone.standard_utc_offset_h(-32.89, -68.84), -3.0)
        self.assertEqual(timezone.standard_utc_offset_h(28.6, 77.2), 5.5)
        self.assertEqual(timezone.standard_utc_offset_h(40.4, -3.7), 1.0)      # Madrid: January, not the summer +2

    def test_a_place_without_a_zone_and_a_missing_database_give_none(self):
        with mock.patch("timezonefinder.TimezoneFinder.timezone_at", return_value=None):
            self.assertIsNone(timezone.standard_utc_offset_h(0.0, -30.0))
        with mock.patch.dict(sys.modules, {"timezonefinder": None}):
            self.assertIsNone(timezone.standard_utc_offset_h(-32.89, -68.84))
