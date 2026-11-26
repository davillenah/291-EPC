"""The public entry points of the 3D side of the architecture reader (OPT-02, ADR-0040): `building_solids` and `draw_elevation`.

Each takes one typed input with the floor as data (the walls and openings the platform keeps of a recognised floor, in metres of its plan) and the IRAM sheet as data (`template`); nothing is read from the
process environment and no process is started. `model3d.building_solids`, `sections.elevation` and `sections.write_view_dxf` stay as the lower-level calls, so the files are the same bytes."""
from dataclasses import dataclass
from typing import Any, List, Mapping, Optional


@dataclass(frozen=True)
class FloorInput:
    """One floor as the platform keeps it, with the heights of its storey."""
    backdrop: Mapping[str, Any]        # {"walls": [{a, b, thickness_m}], "openings": [{kind, at, width_m, angle}]}
    floor: str                         # the level name
    heights: Mapping[str, float]       # {"elevation_m", "wall_height_m", ...}


@dataclass(frozen=True)
class ElevationInput:
    """An elevation of one floor seen from one side, on the IRAM sheet given as `template` (None: the engine's default sheet)."""
    floor: FloorInput
    side: str                          # "north", "south", "east" or "west"
    template: Optional[Any] = None


def building_solids(entrada: FloorInput) -> List[dict]:
    """The solids of the walls and openings of one floor, ready for the 3D scene."""
    if not isinstance(entrada, FloorInput):
        raise TypeError("building_solids() takes a FloorInput")
    from epc_draw.arch import model3d
    return model3d.building_solids(model3d.from_backdrop(dict(entrada.backdrop), entrada.floor), dict(entrada.heights))


def draw_elevation(entrada: ElevationInput, path: Any) -> str:
    """Writes the elevation of one floor to `path` as a DXF on its IRAM sheet; returns the file name."""
    if not isinstance(entrada, ElevationInput):
        raise TypeError("draw_elevation() takes an ElevationInput")
    from epc_draw.arch import model3d, sections
    arch = model3d.from_backdrop(dict(entrada.floor.backdrop), entrada.floor.floor)
    view = sections.elevation(arch, entrada.side, dict(entrada.floor.heights))
    return sections.write_view_dxf(view, arch, path, template=entrada.template)
