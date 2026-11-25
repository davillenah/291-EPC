"""Fasteners and supports of a tray as 3D meshes, all by code: bolt, nut, washer, threaded rod, coupler, strut channel, rod clamp, wall bracket, heavy bracket. Pure geometry: sizes arrive as
arguments (metres), the result is {"vertices": [[x, y, z]], "faces": [[i, j, k, l]]} like the rest of the 3D scene. Every part lies along +x from the origin (a round part is centred on the x axis)."""
import math
from typing import Any, Dict, List, Sequence, Tuple

from . import tray_solid as T

Mesh = Dict[str, list]
AXES = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def _new() -> Tuple[List[List[float]], List[List[int]]]:
    return [], []


def join(*meshes: Mesh) -> Mesh:
    """Several meshes as one."""
    vertices: List[List[float]] = []
    faces: List[List[int]] = []
    for m in meshes:
        shift = len(vertices)
        vertices.extend(m["vertices"])
        faces.extend([[i + shift for i in f] for f in m["faces"]])
    return {"vertices": vertices, "faces": faces}


def moved(mesh: Mesh, dx: float = 0.0, dy: float = 0.0, dz: float = 0.0) -> Mesh:
    return {"vertices": [[v[0] + dx, v[1] + dy, v[2] + dz] for v in mesh["vertices"]], "faces": mesh["faces"]}


def prism(radius: float, length: float, sides: int, x0: float = 0.0, inner: float = 0.0, turn: float = 0.0) -> Mesh:
    """A round or hexagonal prism along x (`sides` 6 is a hex nut, 16 a cylinder); with `inner` > 0 it is a tube (washer, coupler)."""
    vertices, faces = _new()
    rings = [(radius, x0), (radius, x0 + length)] + ([(inner, x0 + length), (inner, x0)] if inner else [])
    for r, x in rings:
        vertices.extend([[x, r * math.cos(turn + 2 * math.pi * k / sides), r * math.sin(turn + 2 * math.pi * k / sides)] for k in range(sides)])
    for ring in range(len(rings) if inner else 1):
        nxt = (ring + 1) % len(rings) if inner else 1
        for k in range(sides):
            a, b = ring * sides + k, ring * sides + (k + 1) % sides
            faces.append([a, b, nxt * sides + (k + 1) % sides, nxt * sides + k])
    if not inner:
        faces.extend([[0, k, k + 1] for k in range(1, sides - 1)])                       # the two ends as fans of triangles
        faces.extend([[sides, sides + k + 1, sides + k] for k in range(1, sides - 1)])
    return {"vertices": vertices, "faces": faces}


def _across_corners(flats: float) -> float:
    return flats / math.sqrt(3)


def bolt(q: Dict[str, float]) -> Mesh:
    """A hex-head bolt: the head at x = 0 and the shank of `bolt_len_m` after it."""
    head = prism(_across_corners(q["head_flats_m"]), q["head_h_m"], 6)
    shank = prism(q["bolt_m"] / 2, q["bolt_len_m"], int(q["sides"]), x0=q["head_h_m"])
    return join(head, shank)


def nut(q: Dict[str, float]) -> Mesh:
    return prism(_across_corners(q["head_flats_m"]), q["nut_h_m"], 6)


def washer(q: Dict[str, float]) -> Mesh:
    return prism(q["washer_d_m"] / 2, q["washer_t_m"], int(q["sides"]), inner=q["bolt_m"] / 2 + 0.0005)


def rod(q: Dict[str, float]) -> Mesh:
    return prism(q["rod_m"] / 2, q["rod_len_m"], int(q["sides"]))


def coupler(q: Dict[str, float]) -> Mesh:
    return prism(q["coupler_d_m"] / 2, q["coupler_len_m"], int(q["sides"]), inner=q["rod_m"] / 2)


def clamp(q: Dict[str, float]) -> Mesh:
    """A rod clamp: a block with the rod hole's worth of material around it."""
    vertices, faces = _new()
    T._box(vertices, faces, (q["clamp_m"] / 2, 0.0, 0.0), AXES, (q["clamp_m"], q["clamp_m"], q["strut_t_m"] * 2))
    return {"vertices": vertices, "faces": faces}


def ceiling_plate(q: Dict[str, float]) -> Mesh:
    vertices, faces = _new()
    T._box(vertices, faces, (q["plate_thick_m"] / 2, 0.0, 0.0), AXES, (q["plate_thick_m"], q["plate_m"], q["plate_m"]))
    return join({"vertices": vertices, "faces": faces}, moved(prism(q["rod_m"] / 2, q["plate_m"] / 2, int(q["sides"])), q["plate_thick_m"]))


def strut(q: Dict[str, float], length: float = 0.0) -> Mesh:
    """A strut channel: a C section (`strut_m` square, `strut_t_m` thick, the lips turned in) of the given length along x."""
    w, t, n = q["strut_m"], q["strut_t_m"], length or q["strut_len_m"]
    vertices, faces = _new()
    for y, z, sy, sz in ((0.0, -w / 2 + t / 2, w, t), (-w / 2 + t / 2, 0.0, t, w), (w / 2 - t / 2, 0.0, t, w), (-w / 4, w / 2 - t / 2, w / 2, t), (w / 4, w / 2 - t / 2, w / 2, t)):
        T._box(vertices, faces, (n / 2, y, z), AXES, (n, sy, sz))
    return {"vertices": vertices, "faces": faces}


def trapeze(q: Dict[str, float], width: float, drop: float) -> Mesh:
    """A trapeze hanger for a tray `width` wide: the strut under it and the two rods that go up `drop`."""
    span = width + 2 * q["overhang_m"]
    bar = strut(q, span)
    turned = {"vertices": [[v[2], v[0] - span / 2, v[1]] for v in bar["vertices"]], "faces": bar["faces"]}      # across (y), not along x
    up = prism(q["rod_m"] / 2, drop, int(q["sides"]))
    standing = {"vertices": [[v[2], v[1], v[0]] for v in up["vertices"]], "faces": up["faces"]}
    rods = [moved(standing, 0.0, y, q["strut_m"] / 2) for y in (-(width / 2 + q["overhang_m"] / 2), width / 2 + q["overhang_m"] / 2)]
    return join(turned, *rods)


def wall_bracket(q: Dict[str, float], width: float, reach: float, arm: float, plate: float, plate_height: float) -> Mesh:
    """A bracket for the wall at x = reach: the arm under the tray (`reach` + half the tray) and the backplate on the wall; z = 0 is the underside of the tray."""
    vertices, faces = _new()
    length = reach + width / 2
    T._box(vertices, faces, (reach - length / 2, 0.0, -arm / 2), AXES, (length, arm, arm))
    T._box(vertices, faces, (reach - q["plate_thick_m"] / 2, 0.0, -plate_height / 2), AXES, (q["plate_thick_m"], plate, plate_height))
    return {"vertices": vertices, "faces": faces}


def heavy_bracket(q: Dict[str, float], width: float) -> Mesh:
    """A heavy bracket: a long arm, a taller backplate and a diagonal brace from the plate up to the arm, for a wide tray with a heavy load."""
    reach = q["heavy_reach_m"]
    arm = q["heavy_arm_m"] / 2
    base = wall_bracket(q, width, reach, arm, q["plate_m"], q["heavy_plate_height_m"])
    angle = math.radians(q["heavy_brace_deg"])
    brace_len = (reach / 2) / math.cos(angle)
    u = (math.cos(angle), 0.0, -math.sin(angle))
    vertices, faces = _new()
    T._box(vertices, faces, (reach - reach / 4, 0.0, -arm - reach / 4 * math.tan(angle)), (u, (0.0, 1.0, 0.0), (math.sin(angle), 0.0, math.cos(angle))), (brace_len, arm / 2, arm / 2))
    return join(base, {"vertices": vertices, "faces": faces})
