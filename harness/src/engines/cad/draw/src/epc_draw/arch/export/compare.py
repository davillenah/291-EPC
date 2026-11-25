"""Compares two renderings of the same drawing (the PNG against the PDF rasterized, say): mean structural similarity (SSIM) of their grey levels, with a 7x7 window."""
import numpy as np
from PIL import Image


def _box(x: np.ndarray, k: int = 7) -> np.ndarray:
    c = np.cumsum(np.cumsum(np.pad(x, ((1, 0), (1, 0))), 0), 1)
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def ssim(a: Image.Image, b: Image.Image) -> float:
    """1.0 for identical pictures. The second is resized to the first when their sizes differ by a pixel or so."""
    a, b = a.convert("L"), b.convert("L").resize(a.size)
    x, y = np.asarray(a, float), np.asarray(b, float)
    mx, my = _box(x), _box(y)
    vx, vy, cov = _box(x * x) - mx ** 2, _box(y * y) - my ** 2, _box(x * y) - mx * my
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    return float((((2 * mx * my + c1) * (2 * cov + c2)) / ((mx ** 2 + my ** 2 + c1) * (vx + vy + c2))).mean())
