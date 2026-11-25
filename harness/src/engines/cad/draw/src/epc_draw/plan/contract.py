"""The public entry point of the floor plan (OPT-02, ADR-0040): `draw_plan(entrada, path)`.

Two calls become one: the document goes through `core.process` and the result through `dxfout.write_dxf`. `PlanInput` holds everything the drawing needs; nothing is read from the process
environment. `process` and `write_dxf` stay as the lower-level calls, so the bytes are the same."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Mapping, Optional, Tuple

from epc_draw.plan import core, dxfout


@dataclass(frozen=True)
class PlanInput:
    """Everything one plan drawing needs."""
    document: Mapping[str, Any]                      # the drawing document (schema/input.schema.json)
    rules: Optional[Tuple[Mapping[str, Any], ...]] = None   # clash rules (None: the default rules)
    version: str = ""                                # DXF version ("" = the default of the engine)
    layers_file: Optional[str] = None
    backdrop: Optional[Mapping[str, Any]] = None     # the walls and room names of the building under the services
    paper_scale: Optional[int] = None                # the N of 1:N of the sheet it will be placed on
    luxmap: Optional[Mapping[str, Any]] = None       # the lux map of the floor


def draw_plan(entrada: PlanInput, path: Any) -> Tuple[dict, List[str]]:
    """Processes the document and writes its DXF to `path`; returns (the result document, the warnings of the drawing)."""
    if not isinstance(entrada, PlanInput):
        raise TypeError("draw_plan() takes a PlanInput")
    result = core.process(dict(entrada.document), rules=list(entrada.rules) if entrada.rules is not None else None)
    warnings = dxfout.write_dxf(result, Path(path), version=entrada.version, layers_file=entrada.layers_file,
                                backdrop=dict(entrada.backdrop) if entrada.backdrop is not None else None, paper_scale=entrada.paper_scale,
                                luxmap=dict(entrada.luxmap) if entrada.luxmap is not None else None)
    return result, warnings


@dataclass(frozen=True)
class Model3dInput:
    """Everything the 3D model of a building needs to be written: the scene (`scene3d.merge` of the building and the services) and the sections to cut."""
    scene: Mapping[str, Any]
    sections: Tuple[Mapping[str, Any], ...] = ()     # each {"name", "axis", "at_m", "look", "depth_m"?}
    stamp_date: Optional[str] = None


def draw_model3d(entrada: Model3dInput, out_dir: Any, board: str) -> Tuple[int, dict]:
    """Writes `<board>_model_3d.dxf` and one `<board>_section_<name>.dxf` per section into `out_dir`; returns (faces written, {section name: counts})."""
    if not isinstance(entrada, Model3dInput):
        raise TypeError("draw_model3d() takes a Model3dInput")
    from epc_draw.plan import scene3d
    out = Path(out_dir)
    scene = dict(entrada.scene)
    faces = scene3d.write_dxf(scene, out / f"{board}_model_3d.dxf", stamp_date=entrada.stamp_date)
    cuts = {}
    for s in entrada.sections:
        section = scene3d.cut(scene, s["axis"], s["at_m"], s["look"], s.get("depth_m"))
        cuts[s["name"]] = scene3d.write_section_dxf(section, out / f"{board}_section_{s['name']}.dxf", stamp_date=entrada.stamp_date)
    return faces, cuts
