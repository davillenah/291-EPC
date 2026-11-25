"""More parts of the tray system, by code: carriage bolt, cover retainer bolt, clamps (suspension, fixing, grounding), universal mounting plate, adjustable wall bracket, lateral splice plate and
articulated union. Pure geometry in metres like `tray_hardware`: every part lies along +x from the origin (plates in the y-z plane at x = 0)."""
import math
from typing import Dict

from . import tray_hardware as H, tray_solid as T

Mesh = Dict[str, list]


def _box(centre, size) -> Mesh:
    vertices, faces = [], []
    T._box(vertices, faces, centre, H.AXES, size)
    return {"vertices": vertices, "faces": faces}


def _across(mesh: Mesh) -> Mesh:
    """A part made along x, turned to lie along z (a pin or stud that stands up)."""
    return {"vertices": [[v[2], v[1], v[0]] for v in mesh["vertices"]], "faces": mesh["faces"]}


def carriage_bolt(q: Dict[str, float], diameter: float) -> Mesh:
    """A carriage bolt: a low round head, a square neck under it and the threaded shank."""
    head = H.prism(q["carriage_head_m"] / 2, q["carriage_head_h_m"], int(q["sides"]))
    neck = _box((q["carriage_head_h_m"] + diameter / 4, 0.0, 0.0), (diameter / 2, diameter, diameter))
    shank = H.prism(diameter / 2, q["bolt_len_m"], int(q["sides"]), x0=q["carriage_head_h_m"] + diameter / 2)
    return H.join(head, neck, shank)


def retainer_bolt(q: Dict[str, float]) -> Mesh:
    """The bolt that holds a cover: a wide flat head and the shank."""
    return H.join(H.prism(q["retainer_head_m"] / 2, q["washer_t_m"] * 2, int(q["sides"])), H.prism(q["bolt_m"] / 2, q["bolt_len_m"], int(q["sides"]), x0=q["washer_t_m"] * 2))


def _plate(q: Dict[str, float], width: float, height: float, holes: int) -> Mesh:
    """A flat plate in the y-z plane with `holes` round holes in a row; built as cells with a hole each, so the plate is solid between them."""
    vertices, faces = [], []
    size = width / max(holes, 1)
    for k in range(max(holes, 1)):
        centre = (0.0, -width / 2 + (k + 0.5) * size, 0.0)
        T._hole_cell(vertices, faces, centre, ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)), (size, height), q["mount_hole_m"])
    return {"vertices": vertices, "faces": faces}


def mounting_plate(q: Dict[str, float]) -> Mesh:
    return _plate(q, q["plate_m"], q["plate_m"], 2)


def lateral_splice(q: Dict[str, float], depth: float) -> Mesh:
    return _plate(q, q["splice_len_m"], depth * 0.7, 4)


def suspension_clamp(q: Dict[str, float]) -> Mesh:
    """A suspension clamp: a U strap that hooks over the flange and the stud that goes up to the rod."""
    t, w = q["clamp_t_m"], q["clamp_w_m"]
    strap = H.join(_box((0.0, 0.0, 0.0), (w, w, t)), _box((0.0, -w / 2 + t / 2, w / 2), (w, t, w)), _box((0.0, w / 2 - t / 2, w / 2), (w, t, w)))
    return H.join(strap, H.moved(_across(H.prism(q["rod_m"] / 2, q["washer_d_m"], int(q["sides"]))), 0.0, 0.0, t / 2))


def fixing_clamp(q: Dict[str, float]) -> Mesh:
    """A fixing clamp: an L strap with the bolt that holds it down."""
    t, w = q["clamp_t_m"], q["clamp_w_m"]
    return H.join(_box((0.0, 0.0, 0.0), (w * 2, w, t)), _box((-w + t / 2, 0.0, w / 2), (t, w, w)), H.moved(_across(H.bolt(q)), w / 2, 0.0, t / 2))


def grounding_clamp(q: Dict[str, float]) -> Mesh:
    """A grounding clamp: the block with its clamping bolt."""
    b = q["ground_block_m"]
    return H.join(_box((0.0, 0.0, 0.0), (b, b, b)), H.moved(_across(H.bolt(q)), 0.0, 0.0, b / 2))


def adjustable_bracket(q: Dict[str, float], width: float, reach: float) -> Mesh:
    """A wall bracket whose arm slides on a slotted backplate (the slot is the gap between two halves of the plate) so its height can be set."""
    arm = 0.04
    length = reach + width / 2
    gap, slot = q["adj_slot_m"], q["adj_slot_len_m"]
    plate = q["plate_m"]
    halves = [_box((reach - q["plate_thick_m"] / 2, s * (gap / 2 + (plate - gap) / 4), -slot / 2), (q["plate_thick_m"], (plate - gap) / 2, slot + 0.1)) for s in (-1, 1)]
    return H.join(_box((reach - length / 2, 0.0, -arm / 2), (length, arm, arm)), *halves)


def articulated_union(q: Dict[str, float], depth: float) -> Mesh:
    """An articulated union of two stretches: a plate at each side and the pin they turn on."""
    w, gap = q["union_plate_m"], q["union_gap_m"]
    plates = [_box((s * (w / 2 + gap / 2), 0.0, 0.0), (w, q["splice_thick_m"], depth * 0.7)) for s in (-1, 1)]
    return H.join(*plates, H.moved(_across(H.prism(q["union_pin_m"] / 2, depth * 0.7, int(q["sides"]))), 0.0, 0.0, -depth * 0.35))
