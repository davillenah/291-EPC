"""The solids of a scene as blocks: solids with the same shape (the same mesh up to where it is and a turn of 90 degrees about the vertical) share one block definition and are inserted.

A DXF with thousands of loose faces cannot be handled in a CAD: the same support, rung-and-rail tray section or luminaire is drawn once as a block and inserted where it goes. Pure: a list of
solids in, the block definitions and the insertions out; the same solids give the same blocks, named in order of first use.

    group(solids) -> {"blocks": [{"name", "vertices", "faces"}], "inserts": [{"block", "at": [x, y, z], "rotation": degrees, "solid": id, "layer": name}]}

`vertices` of a block are relative to its insertion point (the first corner of the mesh) and turned to its canonical position; inserting it at `at` turned by `rotation` gives the mesh again.
"""
import re
from typing import Any, Dict, List, Sequence, Tuple

ROTATIONS = (0, 90, 180, 270)
PRECISION = 3                                   # decimals of a metre: two meshes that agree to the millimetre are the same shape


def _turn(p: Sequence[float], degrees: int) -> Tuple[float, float, float]:
    """A point turned about the vertical axis through the origin by a multiple of 90 degrees (exact: no trigonometry)."""
    x, y, z = p
    return {0: (x, y, z), 90: (-y, x, z), 180: (-x, -y, z), 270: (y, -x, z)}[degrees]


def _round(p: Sequence[float]) -> Tuple[float, float, float]:
    return tuple(round(c, PRECISION) + 0.0 for c in p)  # type: ignore[return-value]


def _local(vertices: Sequence[Sequence[float]], degrees: int) -> List[Tuple[float, float, float]]:
    """The mesh relative to its first corner and turned back by `degrees`."""
    o = vertices[0]
    return [_round(_turn((v[0] - o[0], v[1] - o[1], v[2] - o[2]), (360 - degrees) % 360)) for v in vertices]


def canonical(mesh: Dict[str, Any]) -> Tuple[Any, int, List[Tuple[float, float, float]]]:
    """(key, rotation, local vertices) of a mesh: of its four turns the one that sorts first, so meshes that differ by a turn of 90 degrees give the same key."""
    faces = tuple(tuple(f) for f in mesh["faces"])
    best = min(((tuple(_local(mesh["vertices"], d)), d) for d in ROTATIONS))
    return (best[0], faces), best[1], list(best[0])


def _name(solid: Dict[str, Any], n: int) -> str:
    base = re.sub(r"[^A-Za-z0-9]+", "_", "_".join(str(solid[k]) for k in ("kind", "part") if solid.get(k))).strip("_") or "SOLID"
    return f"EPC_{base}_{n:03d}"


def group(solids: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """The block definitions and the insertions that rebuild `solids` (those with no mesh are left out)."""
    names: Dict[Any, str] = {}
    blocks: List[Dict[str, Any]] = []
    inserts: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}
    for s in solids:
        mesh = s.get("mesh")
        if not mesh or not mesh["vertices"]:
            continue
        key, rotation, local = canonical(mesh)
        if key not in names:
            stem = _name(s, 0)[:-4]
            counts[stem] = counts.get(stem, 0) + 1
            names[key] = f"{stem}_{counts[stem]:03d}"
            blocks.append({"name": names[key], "vertices": [list(v) for v in local], "faces": [list(f) for f in mesh["faces"]]})
        inserts.append({"block": names[key], "at": [round(c, 4) for c in mesh["vertices"][0]], "rotation": rotation, "solid": s.get("id"), "layer": s.get("layer") or "0"})
    return {"blocks": blocks, "inserts": inserts}
