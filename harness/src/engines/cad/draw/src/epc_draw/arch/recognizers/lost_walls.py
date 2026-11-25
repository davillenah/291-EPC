"""Walls a reading lost. A picture is read in several ways and the one that closes most rooms is kept; it can still miss a long wall that another reading found whole (an outer wall with windows
whose frames continue its faces is one wall to the first reading and pieces to the others). Such a wall is brought back when the kept reading has nothing along most of it."""
from typing import List

from epc_draw.arch.geometry import dist_point_segment, seg_length
from epc_draw.arch.model import Wall
from epc_draw.arch.recognizers import Context


def _covered(w: Wall, kept: List[Wall], T: float, samples: int) -> float:
    """The share of points along `w` that lie within one wall thickness of a wall that is kept."""
    hit = 0
    for i in range(samples):
        f = (i + 0.5) / samples
        p = (w.a[0] + (w.b[0] - w.a[0]) * f, w.a[1] + (w.b[1] - w.a[1]) * f)
        hit += any(dist_point_segment(p, k.a, k.b) <= T for k in kept)
    return hit / samples


def lost_walls(first: List[Wall], kept: List[Wall], T: float, ctx: Context) -> List[Wall]:
    cfg = ctx.params["lost_walls"]
    lo, hi = cfg["thickness"]
    return [w for w in first
            if seg_length(w.a, w.b) >= cfg["min_length_in_walls"] * T and lo * T <= w.thickness <= hi * T and _covered(w, kept, T, cfg["samples"]) < cfg["covered_share"]]
