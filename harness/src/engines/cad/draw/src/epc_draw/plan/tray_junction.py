"""The tee and the cross of a tray as one piece: the arms leave the rounded inside corners (arcs of `radius`, the inner radius of the maker) that join the rails of a branch to the rails of the main
run, the rail of the main run with no branch runs through, and no rail crosses the opening. Pure geometry, in metres: `junction_mesh` returns {"vertices", "faces"} or None for the kinds that stay a
crossing of two straights (wire mesh and U channel).

    junction_mesh(kind, width, depth, p, arm, radius, towards) -> mesh | None
        towards: the sides of the branches along y, (1,) for a tee with the branch to +y and (-1, 1) for a cross
"""
import math
from typing import Dict, List, Sequence, Tuple

from . import tray_solid as T

P3 = Tuple[float, float, float]
Mesh = Dict[str, list]


def _join(meshes: Sequence[Mesh]) -> Mesh:
    vertices: List[List[float]] = []
    faces: List[List[int]] = []
    for m in meshes:
        base = len(vertices)
        vertices.extend(m["vertices"])
        faces.extend([[i + base for i in f] for f in m["faces"]])
    return {"vertices": vertices, "faces": faces}


def _corner_arc(sx: int, sy: int, reach: float, steps: int = 8) -> Tuple[List[P3], int]:
    """The axis of the elbow that rounds the inside corner (sx, sy) of a junction (an arc of radius `reach` about the corner point) and the side of the rail that stays: the one nearest the centre."""
    cx, cy = sx * reach, sy * reach
    first, last = math.atan2(-sy, 0.0), math.atan2(0.0, -sx)
    turn = (last - first + math.pi) % (2 * math.pi) - math.pi
    pts = [(cx + reach * math.cos(first + turn * k / steps), cy + reach * math.sin(first + turn * k / steps), 0.0) for k in range(steps + 1)]
    return pts, (1 if turn > 0 else -1)


def _arm(kind: str, width: float, depth: float, p: Dict[str, float], reach: float, arm: float, direction: Tuple[int, int]) -> List[Mesh]:
    """One arm: the deck from the centre to the start of the rails, then the tray with both rails."""
    dx, dy = direction
    near = [(0.0, 0.0, 0.0), (dx * reach, dy * reach, 0.0)]
    far = [(dx * reach, dy * reach, 0.0), (dx * arm, dy * arm, 0.0)]
    return [T.tray_mesh(near, width, depth, p, kind, ()), T.tray_mesh(far, width, depth, p, kind)]


def _through(width: float, depth: float, p: Dict[str, float], reach: float, side: int) -> Mesh:
    """The rail of the main run on the side with no branch, from one rounded corner to the other."""
    vertices: List[List[float]] = []
    faces: List[List[int]] = []
    a, b = (-reach, 0.0, 0.0), (reach, 0.0, 0.0)
    T._rail(vertices, faces, a, b, T._frame(a, b), side, width, depth, p)
    return {"vertices": vertices, "faces": faces}


def junction_mesh(kind: str, width: float, depth: float, p: Dict[str, float], arm: float, radius: float, towards: Sequence[int]) -> "Mesh | None":
    """A tee (`towards` = (1,)) or a cross (`towards` = (-1, 1)): see the module text. `arm` is the length of every arm from the centre."""
    if kind in ("alambre", "canal"):
        return None
    reach = width / 2 + radius
    meshes: List[Mesh] = []
    for direction in [(1, 0), (-1, 0)] + [(0, s) for s in towards]:
        meshes.extend(_arm(kind, width, depth, p, reach, arm, direction))
    for sx in (-1, 1):
        for sy in towards:
            path, side = _corner_arc(sx, sy, reach)
            meshes.append(T.tray_mesh(path, width, depth, p, kind, (side,)))
    if len(towards) == 1:
        meshes.append(_through(width, depth, p, reach, -towards[0]))
    return _join(meshes)
