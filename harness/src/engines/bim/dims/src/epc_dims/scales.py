"""Annotation sizes at a drawing scale.

A text or an arrow is drawn at a size on PAPER (for example 2.5 mm). In model space the same size must be larger by the scale denominator, and it is written in
DRAWING units: a 2.5 mm text at 1:50 is 125 mm in a drawing in millimetres, 12.5 cm in a drawing in centimetres and 0.125 m in a drawing in metres. The scale
is always `1:N` (a reduction); the engine holds no list of scales: the project chooses.
"""
import math

from epc_dims.errors import DimsError


def _positive(value, code_value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise DimsError("err_not_positive_number", name=code_value, value=value)
    return float(value)


def annotation_size(paper_mm, scale_denominator, drawing_unit_mm):
    """The size, in drawing units, of something that measures `paper_mm` on the plotted sheet at the scale `1:scale_denominator`.

    `drawing_unit_mm` is how many millimetres one drawing unit is (1 for a drawing in millimetres, 10 in centimetres, 1000 in metres).
    """
    paper, denominator, unit = _positive(paper_mm, "paper_mm"), _positive(scale_denominator, "scale_denominator"), _positive(drawing_unit_mm, "drawing_unit_mm")
    return round(paper * denominator / unit, 9)


def paper_size(drawing_length, scale_denominator, drawing_unit_mm):
    """The inverse: the length in millimetres on the plotted sheet of `drawing_length` drawing units at the scale `1:scale_denominator`."""
    length, denominator, unit = _positive(drawing_length, "drawing_length"), _positive(scale_denominator, "scale_denominator"), _positive(drawing_unit_mm, "drawing_unit_mm")
    return round(length * unit / denominator, 9)
