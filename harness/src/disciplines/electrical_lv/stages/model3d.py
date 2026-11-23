"""The 3D model, the detail sections and the take-off of stage 10: only when the engineer gives `engine_inputs["model3d"]` on a building run (the floors were routed).

The discipline draws nothing and calculates nothing: per routed floor it hands the walls and openings of the architecture to `epc_arch.model3d` (with the heights the engineer gave) and the routed
plan to `epc_plan.solid`; `epc_plan.detail` turns the runs into the parts they are built from (straights, elbows, tees, reducers) and, when the spacing is given, hangs them from the slab;
`epc_plan.scene3d` writes the model and cuts the sections.

    "model3d": {"floors": {"PB": {"wall_height_m": 2.8, "door_head_m": 2.05, "window_sill_m": 0.9, "window_head_m": 2.1, "slab_m": 0.2, "elevation_m": 0.0}},     # every routed floor, all heights: none is assumed
                "supports": {"spacing_m": 1.5},                               # optional: without it no support is drawn (the spacing comes from the standard and the manufacturer)
                "sections": [{"name": "A", "axis": "x", "at_m": 12.0, "look": "+", "depth_m": 3.0}],     # optional: the detail sections to cut (depth_m optional)
                "elevations": [{"floor": "PB", "side": "S"}]}                  # optional: the elevations of the building of a floor (N, S, E or W), on the IRAM sheet

Files (in the drawings folder, so stage 12 packages them): `<board>_model_3d.dxf`, `<board>_section_<name>.dxf` and `<board>_elevation_<floor>_<side>.dxf`. The take-off goes in the outputs of the stage (`model3d.takeoff`).
The underside of the slab a run hangs from is the level of its floor plus the height of its walls: both given by the engineer.
"""
import copy

from disciplines.electrical_lv.stages.base import StageInputError
from disciplines.electrical_lv.stages.routing_stage import routed_document

ARCH_ENGINE, ARCH_FUNCTION = "cad/arch", "epc_arch.model3d.building_solids"
PLAN_ENGINE, PLAN_FUNCTIONS = "cad/plan", ("epc_plan.solid.solids", "epc_plan.detail.parts", "epc_plan.scene3d.write_dxf")
SECTION_KEYS = {"name", "axis", "at_m", "look", "depth_m"}
KEYS = {"floors", "supports", "sections", "elevations"}
SIDES = ("N", "S", "E", "W")


def _is_section(s):
    """A section has its keys and a name that can be part of a file name (the plane itself is judged by the engine)."""
    if not isinstance(s, dict) or not set(s) <= SECTION_KEYS or not {"name", "axis", "at_m", "look"} <= set(s):
        return False
    return isinstance(s["name"], str) and s["name"].isalnum()


def _is_elevation(e, routing):
    return isinstance(e, dict) and set(e) == {"floor", "side"} and e["floor"] in routing and e["side"] in SIDES


def _elevation_errors(elevations, routing):
    if not isinstance(elevations, list):
        return ["model3d/elevations: a list of {floor, side}"]
    out = [f"model3d/elevations: {e!r} is not {{floor: a routed floor, side: N|S|E|W}}" for e in elevations if not _is_elevation(e, routing)]
    return out + [f"model3d/elevations: {e!r} is given twice" for i, e in enumerate(elevations) if e in elevations[:i]]


def _is_supports(given):
    return isinstance(given, dict) and set(given) <= {"spacing_m", "rod_m", "channel_m", "overhang_m"} and "spacing_m" in given


def _floor_errors(floors, routing):
    from epc_arch.sections import heights_errors
    out = [f"model3d/floors: floor {f} is not a routed floor" for f in sorted(set(floors) - set(routing))]
    out += [f"model3d/floors: the heights of floor {f} are required" for f in sorted(set(routing) - set(floors))]
    return out + [f"model3d/floors/{f}: {e}" for f in sorted(set(floors) & set(routing)) for e in heights_errors(floors[f])]


def _section_errors(sections):
    if not isinstance(sections, list):
        return ["model3d/sections: a list of {name, axis, at_m, look}"]
    out = [f"model3d/sections/{i}: {{name (letters and digits), axis x|y, at_m, look +|-, depth_m?}}" for i, s in enumerate(sections) if not _is_section(s)]
    names = [s["name"] for s in sections if _is_section(s)]
    return out + [f"model3d/sections: the name {n} is used twice" for n in sorted({n for n in names if names.count(n) > 1})]


def errors_of(given, routing):
    """What is wrong with the `model3d` section for the routed floors (empty when the model can be built)."""
    if not isinstance(given, dict) or set(given) - KEYS or not isinstance(given.get("floors"), dict):
        return ["model3d: {floors: {floor id: heights}, supports?: {spacing_m}, sections?: [...]}"]
    out = _floor_errors(given["floors"], routing)
    if "supports" in given and not _is_supports(given["supports"]):
        out.append("model3d/supports: {spacing_m, rod_m?, channel_m?, overhang_m?}")
    return out + _section_errors(given.get("sections", [])) + _elevation_errors(given.get("elevations", []), routing)


def _building(design, floor, heights):
    """The solids of the building of one floor, from the walls and openings of its architecture."""
    from epc_arch import FloorInput, building_solids
    backdrop = design.get("backdrop")
    if not backdrop or not backdrop.get("walls"):
        raise StageInputError([f"model3d: floor {floor} has no architecture in metres to build from"])
    return building_solids(FloorInput(backdrop=backdrop, floor=floor, heights=heights))


def _raised(item, dz, floor):
    """A solid of the services at the level of its floor (the plan engine measures heights from the floor)."""
    out = dict(item, level=floor, path=[[p[0], p[1], round(p[2] + dz, 4)] for p in item["path"]])
    return out


def _services(design, floor, heights):
    """The solids of the routed plan of one floor, at its level."""
    from epc_plan import solid
    doc = routed_document(design)
    doc["plan"] = dict(doc["plan"], level="L0")
    return [_raised(s, heights["elevation_m"], floor) for s in solid.solids(doc, floor, story_height_m=0.0)]


def _hangers(given):
    """The spec of the supports, with the underside of the slab over each floor (its level plus the height of its walls); None when no spacing was given."""
    if "supports" not in given:
        return None
    under = {f: h["elevation_m"] + h["wall_height_m"] for f, h in given["floors"].items()}
    return dict(copy.deepcopy(given["supports"]), slab_underside_m=under)


def build(given, routing):
    """(scene, parts) of the whole building: the building and the equipment as they are, the runs as their parts and, when asked, their supports."""
    from epc_plan import detail, scene3d, solid
    building, services = [], []
    for floor in sorted(routing):
        heights = given["floors"][floor]
        building += _building(routing[floor], floor, heights)
        services += _services(routing[floor], floor, heights)
    hangers = _hangers(given)
    parts = detail.parts(services) + (detail.supports(services, hangers) if hangers else [])
    boxes = [s for s in services if s["shape"] != "run"]
    whole = scene3d.merge([{"schema_version": "1.0", "units": "m", "solids": building, "box": None}, solid.scene(boxes + parts)])
    return whole, parts


def _elevations(given, routing, out_dir, board):
    """Writes the elevations asked for: `{"<floor>_<side>": path}` of the files, each on its IRAM sheet at the scale that fits."""
    from epc_arch import ElevationInput, FloorInput, draw_elevation, template_from_svg
    from epc_titleblock import build as iram_sheet
    template = template_from_svg(iram_sheet("A1", False, None, False, None)["svg"]) if given.get("elevations") else None      # the IRAM sheet goes to the engine as data
    done = {}
    for e in given.get("elevations", []):
        floor = e["floor"]
        path = out_dir / f"{board}_elevation_{floor}_{e['side']}.dxf"
        done[f"{floor}_{e['side']}"] = draw_elevation(ElevationInput(floor=FloorInput(backdrop=routing[floor]["backdrop"], floor=floor, heights=given["floors"][floor]), side=e["side"], template=template), path)
    return done


def write(context_inputs, out_dir, board, stamp_date=None):
    """Writes the model and the sections of a building run when `model3d` was given; returns ({"model3d": outputs}, engine calls), both empty when it was not."""
    given, routing = context_inputs.get("model3d"), context_inputs.get("routing")
    if given is None:
        return {}, []
    if not routing:
        raise StageInputError(["model3d: it needs a building run (the floors routed from their plans)"])
    bad = errors_of(given, routing)
    if bad:
        raise StageInputError(bad)
    from epc_plan import Model3dInput, core, detail, draw_model3d
    try:
        scene, parts = build(given, routing)
        faces, cuts = draw_model3d(Model3dInput(scene=scene, sections=tuple(given.get("sections", [])), stamp_date=stamp_date), out_dir, board)
    except (core.PlanError, ValueError) as exc:
        raise StageInputError([f"model3d: {exc}"]) from exc
    try:
        elevations = _elevations(given, routing, out_dir, board)
    except (ValueError, KeyError) as exc:
        raise StageInputError([f"model3d: {exc}"]) from exc
    outputs = {"solids": len(scene["solids"]), "faces": faces, "sections": cuts, "elevations": elevations, "takeoff": detail.takeoff(parts)}
    return {"model3d": outputs}, [(ARCH_ENGINE, ARCH_FUNCTION)] + ([(ARCH_ENGINE, "epc_arch.sections.elevation")] if elevations else []) + [(PLAN_ENGINE, f) for f in PLAN_FUNCTIONS]
