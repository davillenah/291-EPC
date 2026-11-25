"""The catalog of DXF layers: what every drawing is delivered with (name, colour, line weight, line type, state).

A drawing asks for a layer by its ROLE (`sld.diagram`, `sld.text`, `plan.ELEC-LUM`...), never by a name written in the code. The catalog says what that role is called and how it looks.
Three sources, the later one winning role by role (a file may carry only the roles or fields it changes):
  1. `harness/config/dxf/layers.json`, the file the values live in: open it with any text editor, change a name, colour, weight or line type, save;
  2. the same file name in another folder named by the settings in force (`epc_dxf.settings`, `config_dir`);
  3. the global file the platform's MASTER edits, named by the settings (`layer_files`);
  4. files passed to `load` (later: the project's own file).
The settings are handed in by the caller (`settings.use`); the process environment is never read here (ADR-0042).
"""
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_FILE = Path(__file__).resolve().parents[7] / "config" / "dxf" / "layers.json"      # harness/config/dxf: the file the values live in (one source)
DISCIPLINES_FILE = Path(__file__).resolve().parent / "data" / "disciplines.json"
LINEWEIGHTS = (0.0, 0.05, 0.09, 0.13, 0.15, 0.18, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.53, 0.6, 0.7, 0.8, 0.9, 1.0, 1.06, 1.2, 1.4, 1.58, 2.0, 2.11)      # mm: the ones DXF knows
LINETYPES = ("CONTINUOUS", "DASHED", "DASHDOT", "CENTER", "HIDDEN", "PHANTOM", "DOT")
FLAGS = ("on", "frozen", "locked", "plot")
LOOK_FIELDS = ("color", "lineweight", "linetype")
FORBIDDEN_IN_NAME = '<>/\\":;?*|=`'
BLANK = {"name": "", "color": 7, "lineweight": None, "linetype": "CONTINUOUS", "on": True, "frozen": False, "locked": False, "plot": True}


def _read(path: Path) -> Dict[str, dict]:
    return json.loads(path.read_text(encoding="utf-8-sig")).get("layers", {})


def _editable_file() -> List[str]:
    """The layer file of the editable folder (`harness/config/dxf`), when there is one."""
    from epc_draw.core import textstyle
    folder = textstyle.config_dir()
    return [str(folder / "layers.json")] if folder and folder.resolve() != DEFAULT_FILE.parent.resolve() else []


def _files(*extra: Any) -> List[Path]:
    """The override files in order of authority: those the settings in force name, then `extra` (each a path or a list of paths)."""
    from epc_draw.core import settings
    named = _editable_file() + list(settings.current().layer_files)
    flat = [y for x in extra for y in (x if isinstance(x, (list, tuple)) else [x]) if y]
    return [Path(x) for x in [*named, *flat]]


def load(*extra: Any) -> Dict[str, dict]:
    """The catalog: role -> attributes, the default one overridden, in order, by the files of the settings in force (the global one, the company's, the project's) and by `extra` (those that exist)."""
    out = {role: dict(a) for role, a in _read(DEFAULT_FILE).items()}
    for p in _files(*extra):
        if p.is_file():
            for role, a in _read(p).items():
                out[role] = {**out.get(role, {}), **a}
    return out


def defaults() -> Dict[str, dict]:
    """The catalog that travels with the package, without any override."""
    return {role: dict(a) for role, a in _read(DEFAULT_FILE).items()}


def override_of(catalog: Dict[str, dict], base: Optional[Dict[str, dict]] = None) -> Dict[str, dict]:
    """What a catalog changes with respect to a base (the default catalog when none is given): role -> only the fields that differ. It is what a file at that level stores."""
    base = defaults() if base is None else base
    out: Dict[str, dict] = {}
    for role, a in catalog.items():
        diff = {k: v for k, v in a.items() if k != "description" and base.get(role, {}).get(k) != v}
        if diff:
            out[role] = diff
    return out


def resolve(catalog: Optional[Dict[str, dict]] = None) -> Dict[str, dict]:
    """The catalog given, or the one in force (default, global file) when none is given."""
    return catalog if catalog is not None else load()


def get(role: str, catalog: Optional[Dict[str, dict]] = None) -> dict:
    """The attributes of a role; a role the catalog does not know gets plain defaults under the role's own name."""
    cat = resolve(catalog)
    return {**BLANK, "name": role.split(".", 1)[-1], **cat.get(role, {})}


def name(role: str, catalog: Optional[Dict[str, dict]] = None) -> str:
    return get(role, catalog)["name"]


def apply(doc, role: str, catalog: Optional[Dict[str, dict]] = None) -> str:
    """Make sure the layer of `role` is in the ezdxf document with its attributes; returns its name."""
    a = get(role, catalog)
    lay = doc.layers.get(a["name"]) if a["name"] in doc.layers else doc.layers.add(a["name"])
    lay.color = int(a["color"])
    lay.dxf.linetype = doc.linetypes.get(a["linetype"]).dxf.name if a["linetype"] in doc.linetypes else "Continuous"       # the name as the document writes it
    _set_flags(lay, a)
    return a["name"]


def _set_flags(lay, a: dict) -> None:
    if a["lineweight"] is not None:                 # empty: the layer keeps the standard weight (what drawings had before the catalog)
        lay.dxf.lineweight = int(round(float(a["lineweight"]) * 100))
    lay.on, lay.is_frozen, lay.is_locked = bool(a["on"]), bool(a["frozen"]), bool(a["locked"])
    lay.description = (a.get("description") or {}).get("en") or lay.description      # in the LAYER table: every layer of a deliverable has one
    if not a["plot"]:
        lay.dxf.plot = 0


def logo_layer_name(company: str) -> str:
    """The layer of a company logo, `0-Logo-<Company>`: the name of the provider or of the client without spaces or symbols (`Energy Sapiens` gives `0-Logo-EnergySapiens`); it comes from the project data."""
    word = "".join(ch for ch in str(company) if ch.isalnum() and ch.isascii())
    if not word:
        from epc_draw.core.errors import DxfError
        raise DxfError("err_logo_layer_company")
    return f"0-Logo-{word}"


def add_logo_layer(doc, company: str, role: str = "provider") -> str:
    """Adds the layer of the logo of `company` (`role`: `provider` or `client`) with its English description; returns its name."""
    name = logo_layer_name(company)
    lay = doc.layers.get(name) if name in doc.layers else doc.layers.add(name)
    lay.color = 7
    lay.dxf.lineweight = 25
    lay.description = f"Logo of the {role} company {company}"
    return name


def describe_layers(doc, catalog: Optional[Dict[str, dict]] = None) -> List[str]:
    """Gives every layer of the document that has no description the English description of the catalog role of the same name; returns the layers still without one
    (the layers `0` and `Defpoints` that every DXF carries are not counted)."""
    by_name = {a["name"]: (a.get("description") or {}).get("en") for a in resolve(catalog).values() if a.get("name")}
    missing = []
    for lay in doc.layers:
        name = lay.dxf.name
        if name in ("0", "Defpoints") or lay.description:
            continue
        if by_name.get(name):
            lay.description = by_name[name]
        else:
            missing.append(name)
    return sorted(missing)


def _name_problems(role: str, a: dict) -> Iterable[str]:
    n = str(a.get("name", "")).strip()
    if not n or len(n) > 255 or any(c in n for c in FORBIDDEN_IN_NAME):
        yield f"{role}.name: required, up to 255 characters, none of {FORBIDDEN_IN_NAME}"


def _look_problems(role: str, a: dict) -> Iterable[str]:
    if not isinstance(a.get("color"), int) or isinstance(a.get("color"), bool) or not 1 <= a["color"] <= 255:
        yield f"{role}.color: a whole number from 1 to 255 (AutoCAD colour index)"
    if a.get("lineweight") is not None and a.get("lineweight") not in LINEWEIGHTS:
        yield f"{role}.lineweight: empty (standard) or one of {', '.join(str(x) for x in LINEWEIGHTS)} mm"
    if a.get("linetype") not in LINETYPES:
        yield f"{role}.linetype: one of {', '.join(LINETYPES)}"


def _problems(role: str, a: dict) -> Iterable[str]:
    yield from _name_problems(role, a)
    yield from _look_problems(role, a)
    yield from (f"{role}.{f}: true or false" for f in FLAGS if not isinstance(a.get(f), bool))


def validate(catalog: Dict[str, dict]) -> Dict[str, str]:
    """{field: message} for what a catalog may not contain; empty when it is valid. Two roles may share a layer name (one layer for one element that two engines draw) only if they look the same."""
    errors: Dict[str, str] = {}
    seen: Dict[str, str] = {}
    for role, a in catalog.items():
        for msg in _problems(role, a):
            errors[msg.split(":")[0]] = msg.split(": ", 1)[1]
        other = seen.setdefault(str(a.get("name", "")).strip().lower(), role)
        if _looks_differ(a, catalog[other]):
            errors[f"{role}.name"] = f"already used by {other} with another look (colour, line type or weight)"
    return errors


def _looks_differ(a: dict, b: dict) -> bool:
    return any(a.get(k) != b.get(k) for k in LOOK_FIELDS)


def dump(catalog: Dict[str, dict], path: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps({"schema_version": "1.0", "layers": catalog}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


# ---------------------------------------------------------------- the layers of each discipline
def disciplines() -> List[dict]:
    """The disciplines the layers are grouped by: id, prefix of the layer names, names and the drawing profile of the plan editor (None: no tools of its own yet). Data, in `data/disciplines.json`."""
    return json.loads(DISCIPLINES_FILE.read_text(encoding="utf-8-sig"))["disciplines"]


def aci_hex(aci: int) -> str:
    """An AutoCAD colour index as `#rrggbb` (7 is drawn as black on white paper)."""
    from ezdxf import colors
    return "#000000" if aci == 7 else colors.aci2rgb(aci).to_hex()[:7]


def _in_discipline(role: str, d: dict) -> bool:
    """A role belongs to a discipline by the element name in its key (`plan.ELEC-CABLE` starts with `ELEC-`) or by the prefix of the role (`arch.`, `pv.`, `sld.`): the layer name follows the NCS convention and carries no such group."""
    element = role.split(".", 1)[-1]
    return element.startswith(d["prefix"]) or role.startswith(tuple(d.get("role_prefixes", [])))


def by_discipline(catalog: Optional[Dict[str, dict]] = None) -> List[dict]:
    """The catalog grouped by discipline, in the order of `disciplines()`: each with its layers (role, name, colour as the index and as hex, line type and weight, state, description).
    A role goes to the discipline whose prefix its element name starts with, or whose role prefix it has; one that matches none is left out."""
    cat = resolve(catalog)
    out = []
    for d in disciplines():
        mine = [{"role": role, "name": a["name"], "color": a["color"], "hex": aci_hex(a["color"]), "linetype": a.get("linetype", "CONTINUOUS"), "lineweight": a.get("lineweight"),
                 "on": a.get("on", True), "description": a.get("description", {})} for role, a in cat.items() if _in_discipline(role, d)]
        out.append({**d, "layers": sorted(mine, key=lambda x: x["name"])})
    return out
