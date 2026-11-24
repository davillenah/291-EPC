"""The fittings of a ladder tray seen from above, as lines: pure geometry in the local frame of the fitting (the caller moves and turns them).

Every fitting is drawn with the same sizes as the straight tray (`tray_draw`). The frame: the main run goes along +x and passes through the origin; a branch goes towards -y. `arm` is
the length drawn on each side of the junction, `radius` the inside radius of the bends (the catalogue gives 300 mm). Kinds: elbow90, elbow45, elbow_adjustable, tee, cross,
reduction_central, reduction_side, end, cover, `vertical_bend` (side view), plus the supports `bracket_wall` and `bracket_heavy`. Nothing is read from files or the environment.
"""
import math
from typing import Callable, Dict, List, Sequence, Tuple

from epc_plan.core import PlanError
from . import tray_draw

Point = Tuple[float, float]
Line = Tuple[Point, Point]


def _ladder(pts: Sequence[Point], width: float, p: Dict[str, float]) -> List[Line]:
    return tray_draw.tray_lines(pts, "escalera", width, p)


def _bend(width: float, p, degrees: float, arm: float) -> List[Line]:
    """A bend of `degrees` (to the left) between two arms of length `arm`."""
    a = math.radians(degrees)
    corner = (arm, 0.0)
    end = (arm + arm * math.cos(a), arm * math.sin(a))
    return _ladder([(0.0, 0.0), corner, end], width, p)


def elbow90(width, p, arm=None, **_):
    return _bend(width, p, 90.0, arm or 4 * width)


def elbow45(width, p, arm=None, **_):
    return _bend(width, p, 45.0, arm or 4 * width)


def elbow_adjustable(width, p, degrees: float = 60.0, arm=None, **_):
    """The adjustable elbow (any angle between 0 and 90 degrees)."""
    return _bend(width, p, degrees, arm or 4 * width)


def _arc(centre: Point, radius: float, first: float, turn: float, steps: int = 8) -> List[Line]:
    pts = [(centre[0] + radius * math.cos(first + turn * k / steps), centre[1] + radius * math.sin(first + turn * k / steps)) for k in range(steps + 1)]
    return list(zip(pts, pts[1:]))


def _junction(width: float, p, arm: float, sides: Sequence[int]) -> List[Line]:
    """A tee (branch towards -y) or a cross (`sides` holds -1 and +1 for the branches): the arms leave the arcs that join the rails of the branch to the rails of the main run."""
    h, r = width / 2, p["radius"]
    reach = h + r
    lines: List[Line] = []
    for sx in (-1, 1):                                              # main run, each side
        lines += _ladder([(sx * reach, 0.0), (sx * max(arm, reach + p["joint_pitch"] / 4), 0.0)], width, p)
    for sy in sides:                                                # branches
        lines += _ladder([(0.0, sy * reach), (0.0, sy * max(arm, reach + p["joint_pitch"] / 4))], width, p)
        for sx in (-1, 1):                                          # the arc between the branch rail and the main rail, centred on the corner of the two
            first = math.pi if sx == 1 else 0.0
            turn = (-sy * math.pi / 2 - first + math.pi) % (2 * math.pi) - math.pi
            lines += _arc((sx * reach, sy * reach), r, first, turn)
    if len(sides) == 1:                                             # the main rails on the side with no branch run through
        for d in (-sides[0] * h, -sides[0] * (h - p["lip"])):
            lines.append(((-reach, d), (reach, d)))
    return lines


def tee(width, p, arm=None, **_):
    return _junction(width, p, arm or 4 * width, (-1,))


def cross(width, p, arm=None, **_):
    return _junction(width, p, arm or 4 * width, (-1, 1))


def _taper(big: float, small: float, p, length: float, offset: float) -> List[Line]:
    """A reduction: the wide tray, a taper of `length` and the narrow tray; `offset` is how far the narrow axis moves to the side (0 central)."""
    lines = _ladder([(-length, 0.0), (0.0, 0.0)], big, p) + _ladder([(length, offset), (2 * length, offset)], small, p)
    for s in (1, -1):
        lines.append(((0.0, s * big / 2), (length, offset + s * small / 2)))
    return lines


def reduction_central(width, p, small=None, length=None, **_):
    return _taper(width, small or width * 2 / 3, p, length or width * 2, 0.0)


def reduction_side(width, p, small=None, length=None, **_):
    small = small or width * 2 / 3
    return _taper(width, small, p, length or width * 2, (width - small) / 2)


def end(width, p, arm=None, **_):
    """A blind end: a short tray closed by a plate across its end."""
    arm = arm or width
    return _ladder([(0.0, 0.0), (arm, 0.0)], width, p) + [((arm, -width / 2), (arm, width / 2)), ((arm + p["lip"], -width / 2), (arm + p["lip"], width / 2))]


def cover(width, p, arm=None, **_):
    """The lid of a section seen from above: its outline with the two diagonals that mean a cover."""
    arm = arm or 3 * width
    c = [(0.0, -width / 2), (arm, -width / 2), (arm, width / 2), (0.0, width / 2)]
    return [(c[i], c[(i + 1) % 4]) for i in range(4)] + [(c[0], c[2]), (c[1], c[3])]


def bracket_wall(width, p, **_):
    """A wall bracket seen from above: the wall, the plate and the arm that carries the tray."""
    w = width + 2 * p["support_overhang"]
    d = p["support_channel"]
    return [((-d * 3, -d), (-d * 3, w - d)), ((-d * 3 - d, -d), (-d * 3 - d, w - d)), ((-d * 3, 0.0), (0.0, 0.0)), ((-d * 3, w - 2 * d), (0.0, w - 2 * d)), ((0.0, 0.0), (0.0, w - 2 * d))]


def bracket_heavy(width, p, **_):
    return bracket_wall(width, p) + [((-p["support_channel"] * 3, 0.0), (0.0, p["support_channel"] * 4)), ((-p["support_channel"] * 3, p["support_channel"] * 4), (0.0, 0.0))]


def vertical_bend(width, p, depth=None, links: int = 5, **_):
    """The vertical articulated bend (catalogue: 5 links) in side view: x along the run, y up. The axis turns 90 degrees upwards in `links` straight chords; `depth` is the height of the sides."""
    depth = depth or width / 3
    r = p["radius"] + depth
    axis = tray_draw.fillet_path([(0.0, 0.0), (r + depth * 4, 0.0), (r + depth * 4, r + depth * 4)], r, steps=links)
    top, bottom = tray_draw.offset_path(axis, depth / 2), tray_draw.offset_path(axis, -depth / 2)
    return list(zip(top, top[1:])) + list(zip(bottom, bottom[1:])) + [(t, b) for t, b in zip(top[1:-1], bottom[1:-1])]


FITTINGS: Dict[str, Callable[..., List[Line]]] = {f.__name__: f for f in (elbow90, elbow45, elbow_adjustable, tee, cross, reduction_central, reduction_side, end, cover, vertical_bend, bracket_wall, bracket_heavy)}


def fitting_lines(kind: str, width: float, p: Dict[str, float], **options) -> List[Line]:
    """The lines of one fitting in its local frame; `options` are the ones of the kind (`arm`, `degrees`, `small`, `length`)."""
    if kind not in FITTINGS:
        raise PlanError("err_tray_fitting", kind=kind, kinds=", ".join(FITTINGS))
    return FITTINGS[kind](width, p, **options)
