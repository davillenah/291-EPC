"""The 3D model of a photovoltaic plant as a SolidCraft script, written from the same layout and equipment records as the 3D DXF (`model3d`).

SolidCraft is an open-source parametric CAD (`solidcraft-cli`). The engine does not run it (no process, no file): it returns the script, `{"commands": [{"command": ..., "params": ...}]}` as JSON bytes,
and the caller runs `solidcraft-cli run <script> --save <name>.sc --out <name>.step` (`run_arguments`). The model is built the way the owner asked (2026-11-27): light, parametric, parts and assemblies.

* One component per distinct part, defined once: the module of a tilt, the table of an array (modules, width, tilt; its rails and posts), the inverter of a record, the ground and the station.
* Every module, table and inverter of the plant is an instance (`occurrence.copy`) of its component with its own placement, never a second copy of the geometry.
* The material of a part comes from its equipment record (the datasheet read into `epc_pv/data`): the density is the datasheet mass over the outline volume, the name is the record's material text;
  a part whose record does not say gets no material and is listed in `materials` as `pending review`. Nothing is invented. Millimetres, x east, y north, z up, like the DXF.

  render(geometry, result, name, stamp_date, parts, level) -> {"file": `<name>_pv_model_3d_solidcraft.json`, "bytes": script, "components": n, "instances": n, "materials": [...]}
  run_arguments(file, name) -> the arguments of `solidcraft-cli` that make `<name>_pv_model_3d.sc` and `<name>_pv_model_3d.step`
"""
import json
import math
from typing import Any, Dict, List, Optional, Tuple

from epc_draw.pv import model3d as m3
from epc_draw.pv import parts as pv_parts
from epc_drawing import DrawingError

MM = 1000.0
STEEL_WORDS, ALUMINIUM_WORDS = ("steel", "acero"), ("aluminium", "aluminum", "aluminio")
BUILT_IN = {"steel": "Steel", "aluminium": "Aluminum"}       # names of the SolidCraft material library; their density is SolidCraft's, not ours


class Script:
    """The commands of a script, the names already used and the materials listed."""

    def __init__(self) -> None:
        self.commands: List[Dict[str, Any]] = []
        self.names: Dict[str, int] = {}
        self.components: Dict[str, Any] = {}
        self.instances = 0
        self.materials: List[Dict[str, Any]] = []
        self.made: Dict[str, str] = {}

    def add(self, command: str, **params: Any) -> None:
        self.commands.append({"command": command, "params": params})

    def unique(self, base: str) -> str:
        self.names[base] = self.names.get(base, 0) + 1
        return base if self.names[base] == 1 else f"{base} {self.names[base]}"


def _mm(values) -> List[float]:
    return [round(v * MM, 3) for v in values]


def _weight_kg(record: Optional[Dict[str, Any]]) -> Optional[float]:
    """The mass the datasheet states (`mechanical_ratings.weight_kg` or `mechanical.weight_kg`), or None."""
    for key in ("mechanical_ratings", "mechanical"):
        value = ((record or {}).get(key) or {}).get("weight_kg")
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
    return None


def _source_ids(record: Optional[Dict[str, Any]]) -> List[str]:
    return [s.get("id") for s in (record or {}).get("sources", [])]


def _material(script: Script, part: str, record: Optional[Dict[str, Any]], mass_kg: Optional[float], volume_mm3: float, text: str) -> Optional[str]:
    """Creates (once) the material of a part from the datasheet mass and the outline volume and returns its name; None, listed as pending review, when the record gives no mass."""
    entry = {"part": part, "record": (record or {}).get("id"), "source_ids": _source_ids(record), "material_text": text}
    if mass_kg is None or volume_mm3 <= 0:
        script.materials.append(dict(entry, material=None, status="pending review"))
        return None
    density = round(mass_kg * 1.0e6 / volume_mm3, 6)       # kg -> g and mm3 -> cm3
    name = f"{(record or {}).get('id')} {part}"
    if name not in script.made:
        script.add("material.create", name=name, density_g_cm3=density)
        script.made[name] = name
    script.materials.append(dict(entry, material=name, density_g_cm3=density, status="from datasheet mass over outline volume (record status: %s)" % (record or {}).get("status", "unverified")))
    return name


def _built_in(script: Script, part: str, record: Optional[Dict[str, Any]], text: str) -> Optional[str]:
    """The SolidCraft library material named by the record's material text (steel, aluminium), or None, listed as pending review."""
    low = (text or "").lower()
    kind = "steel" if any(w in low for w in STEEL_WORDS) else "aluminium" if any(w in low for w in ALUMINIUM_WORDS) else None
    entry = {"part": part, "record": (record or {}).get("id"), "source_ids": _source_ids(record), "material_text": text}
    if kind is None:
        script.materials.append(dict(entry, material=None, status="pending review"))
        return None
    script.materials.append(dict(entry, material=BUILT_IN[kind], status="library material named by the datasheet text (record status: %s)" % (record or {}).get("status", "unverified")))
    return BUILT_IN[kind]


def _assign(script: Script, bodies: List[str], material: Optional[str]) -> None:
    if material and bodies:
        script.add("material.assign", bodies=bodies, material=material)


def _component(script: Script, name: str, parent: str, bodies: List[str]) -> None:
    script.add("component.create", name=name, parent=parent, activate=False)
    if bodies:
        script.add("component.move_bodies", bodies=bodies, component=name)
    script.components[name] = True


def _box(script: Script, base: str, corner, size) -> str:
    """A body of its own: a box with its lowest corner at `corner` (metres) and sizes `size` (metres)."""
    name = script.unique(base)
    x, y, z = _mm(corner)
    dx, dy, dz = _mm(size)
    script.add("solid.box", length=dx, width=dy, height=dz, corner=[x, y, z], operation="new", body_name=name)
    return name


def _tilt(script: Script, body: str, origin, tilt_deg: float) -> None:
    """Turns a body about the x axis through `origin` (metres) so the plane falls to the north by `tilt_deg`, as `model3d.tilted_box`."""
    script.add("solid.move", bodies=[body], origin=_mm(origin), axis=[1, 0, 0], angle=-tilt_deg)


def _module_part(script: Script, geometry: Dict[str, Any], parts: Dict[str, Any], table_name: str, tilt_deg: float, rear_h: float) -> str:
    """The module of a tilt, defined once inside the table that first needs it; returns its component name."""
    name = f"Module {tilt_deg:g} deg"
    if name in script.components:
        return name
    dims = geometry["module"]["dimensions_mm"]
    long_m, short_m = dims[0] / MM, dims[1] / MM
    along, across = (short_m, long_m) if geometry["table"]["orientation"] == "portrait" else (long_m, short_m)
    body = _box(script, "Laminate", (0.0, 0.0, rear_h), (along, across, m3.MODULE_M))
    _tilt(script, body, (0.0, 0.0, rear_h), tilt_deg)
    record = parts.get("module")
    layers = {layer.get("id"): layer for layer in (record or {}).get("layers", [])}
    text = (layers.get("front_glass") or {}).get("material") or ""
    _assign(script, [body], _material(script, "laminate", record, _weight_kg(record), along * across * m3.MODULE_M * MM ** 3, text))
    _component(script, name, table_name, [body])
    return name


def _table_supports(script: Script, geometry: Dict[str, Any], parts: Dict[str, Any], width: float, tilt_deg: float, rear_h: float) -> List[str]:
    """The rails and posts of a table at the origin (bodies in the root, not yet in a component), with the material of the structure record."""
    slope, tilt = float(geometry["table"]["slope_m"]), math.radians(tilt_deg)
    bodies, rails, posts = [], [], []
    count = max(int(math.ceil(width / m3.SPACING_M)) + 1, 2)
    embed = m3.embedment_m(geometry)
    for f in (0.25, 0.75):
        s = slope * f
        rail = _box(script, "Rail", (0.0, s - m3.RAIL_M / 2, rear_h - m3.RAIL_DEPTH_M - m3.MODULE_M), (width, m3.RAIL_M, m3.RAIL_DEPTH_M))
        _tilt(script, rail, (0.0, 0.0, rear_h), tilt_deg)
        rails.append(rail)
        top = max(rear_h - s * math.sin(tilt) - m3.RAIL_DEPTH_M - m3.MODULE_M, 0.0)
        for k in range(count):
            x = m3.POST_M / 2 + k * (width - m3.POST_M) / (count - 1)
            posts.append(_box(script, "Post", (x - m3.POST_M / 2, s * math.cos(tilt) - m3.POST_M / 2, -embed), (m3.POST_M, m3.POST_M, top + embed)))
    structure = parts.get("structure")
    text = " ".join(str(m.get("material", "")) for m in (structure or {}).get("materials", []) if "post" in str(m.get("component", "")).lower() or "purlin" in str(m.get("component", "")).lower())
    _assign(script, rails + posts, _built_in(script, "rails and posts", structure, text))
    return rails + posts + bodies


def _table_part(script: Script, geometry: Dict[str, Any], parts: Dict[str, Any], table: Dict[str, Any], tilt_deg: float) -> str:
    """The table of an array, defined once: its modules (instances of the module part), rails and posts; returns its component name."""
    name = f"Table {table['array']} {int(table['modules'])}M {float(table['width_m']):g}W {tilt_deg:g}D"
    if name in script.components:
        return name
    slope = float(geometry["table"]["slope_m"])
    rear_h = float(geometry["module"]["front_clearance_m"] or 0.0) + slope * math.sin(math.radians(tilt_deg))
    support_bodies = _table_supports(script, geometry, parts, float(table["width_m"]), tilt_deg, rear_h)
    _component(script, name, "root", support_bodies)
    module = _module_part(script, geometry, parts, name, tilt_deg, rear_h)
    _place_modules(script, geometry, name, module, table, math.radians(tilt_deg))
    return name


def _place_modules(script: Script, geometry: Dict[str, Any], table_name: str, module: str, table: Dict[str, Any], tilt: float) -> None:
    """Module 2..n of a table as instances of the module part (module 1 is the part itself when the table defined it, else an instance too)."""
    dims, gap = geometry["module"]["dimensions_mm"], geometry["module"]["gap_m"]
    long_m, short_m = dims[0] / MM, dims[1] / MM
    along, across = (short_m, long_m) if geometry["table"]["orientation"] == "portrait" else (long_m, short_m)
    per_row = int(geometry["table"]["modules_per_row"])
    first_here = script.components.get(module) is True
    script.components[module] = table_name
    for i in range(int(table["modules"])):
        r, c = divmod(i, per_row)
        if i == 0 and first_here:
            continue
        step = (c * (along + gap), r * (across + gap) * math.cos(tilt), -r * (across + gap) * math.sin(tilt))
        script.add("occurrence.copy", component=module, parent=table_name, translate=_mm(step))
        script.instances += 1


def _inverter_parts(script: Script, geometry: Dict[str, Any], parts: Dict[str, Any], level: str) -> None:
    """The inverters: one component per record (its envelope), one instance per inverter; the plain pad when the record is missing."""
    records, first = parts.get("inverters") or {}, {}
    for inv in geometry["inverters"]:
        if inv.get("x") is None:
            continue
        record = records.get(inv.get("catalog_id") or inv.get("id"))
        det = pv_parts.inverter_detail(record, level)
        size = det["size"] if det else (inv["width_m"], m3.PAD_HEIGHT_M, inv["depth_m"])
        key = f"Inverter {(record or {}).get('id', 'pad')} {size[0]:g}x{size[2]:g}x{size[1]:g}"
        corner = (inv["x"] - size[0] / 2, inv["y"] - size[2] / 2, 0.0)
        if key not in first:
            body = _box(script, "Enclosure", corner, (size[0], size[2], size[1]))
            _assign(script, [body], _material(script, "enclosure", record, _weight_kg(record), size[0] * size[1] * size[2] * MM ** 3, ""))
            _component(script, key, "root", [body])
            first[key] = corner
        else:
            script.add("occurrence.copy", component=key, translate=_mm([corner[i] - first[key][i] for i in range(3)]))
            script.instances += 1


def _tables(script: Script, geometry: Dict[str, Any], parts: Dict[str, Any]) -> None:
    """Every table of the layout as an instance of its table part (the first of each type is moved to its place, the others are copies)."""
    first: Dict[str, Tuple[float, float]] = {}
    for table in geometry["tables"]:
        tilt_deg = float(geometry["tilts_deg"][table["array"]])
        name = _table_part(script, geometry, parts, table, tilt_deg)
        if name not in first:
            first[name] = (float(table["x"]), float(table["y"]))
            script.add("occurrence.move", occurrence=f"{name}:1", translate=_mm([table["x"], table["y"], 0.0]))
        else:
            script.add("occurrence.copy", component=name, translate=_mm([table["x"] - first[name][0], table["y"] - first[name][1], 0.0]))
        script.instances += 1


def _site(script: Script, geometry: Dict[str, Any]) -> None:
    """The ground and the station, single parts (no material: the records do not give one)."""
    site, st = geometry["site"], geometry["station"]
    ground = _box(script, "Ground", (0.0, 0.0, -m3.SOIL_M), (site["width_m"], site["length_m"], m3.SOIL_M))
    station = _box(script, "Station", (st["x"], st["y"], 0.0), (st["width_m"], st["depth_m"], m3.STATION_HEIGHT_M))
    _component(script, "Ground", "root", [ground])
    _component(script, "Station", "root", [station])
    script.materials.append({"part": "ground", "record": None, "source_ids": [], "material": None, "status": "pending review"})
    script.materials.append({"part": "station", "record": None, "source_ids": [], "material": None, "status": "pending review"})


def render(geometry: Dict[str, Any], result: Dict[str, Any], name: str, stamp_date=None, parts: Optional[Dict[str, Any]] = None, level: str = "standard") -> Dict[str, Any]:
    """The script as data: {"file": `<name>_pv_model_3d_solidcraft.json`, "bytes": the script, "components": n, "instances": n, "materials": [...]}. Nothing is written or run."""
    if not geometry.get("tables"):
        raise DrawingError("err_layout_no_tables")
    parts, script = parts or {}, Script()
    _site(script, geometry)
    _inverter_parts(script, geometry, parts, level)
    _tables(script, geometry, parts)
    data = json.dumps({"commands": script.commands}, ensure_ascii=False, indent=None, separators=(",", ":")).encode("utf-8")
    return {"file": f"{name}_pv_model_3d_solidcraft.json", "bytes": data, "components": len(script.components), "instances": script.instances, "materials": script.materials}


def run_arguments(file: str, name: str) -> List[str]:
    """The arguments of `solidcraft-cli` that run the script `file` and save `<name>_pv_model_3d.sc` (the design) and `<name>_pv_model_3d.step`; `--results` names the step that fails."""
    return ["run", file, "--save", f"{name}_pv_model_3d.sc", "--out", f"{name}_pv_model_3d.step", "--results"]


def write(geometry: Dict[str, Any], result: Dict[str, Any], out_dir, name: str, stamp_date=None, parts: Optional[Dict[str, Any]] = None, level: str = "standard") -> Dict[str, Any]:
    """Writes `<name>_pv_model_3d_solidcraft.json` under `out_dir`. Returns {"script": path, "components": n, "instances": n, "materials": [...]}."""
    from epc_draw.pv import files
    made = render(geometry, result, name, stamp_date, parts, level)
    return {"script": files.save(out_dir, {made["file"]: made["bytes"]})[made["file"]], "components": made["components"], "instances": made["instances"], "materials": made["materials"]}
