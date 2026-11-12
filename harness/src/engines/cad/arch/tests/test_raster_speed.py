"""The faster morphology of the image reader (windows of doubling size) gives exactly what the integral-image definition gives."""
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from epc_arch.sources import raster                                # noqa: E402


def _reference_opening(ink: np.ndarray, k: int) -> np.ndarray:
    full = (2 * k + 1) ** 2
    return raster._box_sum(raster._box_sum(ink, k) == full, k) > 0


def _reference_closing(ink: np.ndarray, r: int) -> np.ndarray:
    grown = raster._box_sum(ink.astype(np.uint8), r) > 0
    return ~(raster._box_sum((~grown).astype(np.uint8), r) > 0)


class TestRasterMorphology(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(7)
        self.pictures = []
        for _ in range(4):
            a = rng.random((110, 85)) > 0.4
            a[15:70, 10:55] = True
            self.pictures.append(a)

    def test_opening_equals_its_definition(self):
        for a in self.pictures:
            for k in (1, 2, 3, 5, 8, 24):
                self.assertTrue((raster.opening(a, k) == _reference_opening(a, k)).all(), k)

    def test_closing_equals_its_definition(self):
        for a in self.pictures:
            for r in (1, 3, 6):
                self.assertTrue((raster.closing(a, r) == _reference_closing(a, r)).all(), r)


if __name__ == "__main__":
    unittest.main()
