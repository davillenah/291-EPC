"""The editable part of a sheet: what an organization may change of the IRAM sheet and how that is checked.

A sheet configuration is a dict, every key optional (what is not said stays as the standard IRAM sheet draws it):

  {"frame": {"margin_left": 25, "margin": 10, "strip": 5},                          mm: the filing margin, the other three margins, the coordinate strip
   "pens":  {"cut": 0.1, "frame": 1.0, "zone": 0.5, "outline": 0.8, "cell": 0.4, "fine": 0.2},    mm: the line weights of the sheet and of its title block
   "text":  {"coordinates": 3.5, "block": 2.0},                                      mm: capital height of the letters of the strip; of the texts of the title block
   "block": {"width": 175, "height": 51, "modifications_height": 21.5,               mm: the box of the title block and of the list of modifications over it
             "elements": [...]}}                                                      the title block as drawn, element by element (None: the standard one)

The elements of the title block are in mm from its upper left corner:
  {"id": "e01", "kind": "line", "group": "line", "x1": 0, "y1": 0, "x2": 175, "y2": 0, "pen": "cell"}        `pen` is a role of `pens` or `w` a width in mm
  {"id": "e02", "kind": "rect", "group": "line", "x": 0, "y": 0, "w": 175, "h": 51, "pen": "outline"}
  {"id": "e03", "kind": "text", "group": "txt|var|rojo", "x": 3, "y": 7, "text": "Proyectado por:", "h": 2.0, "anchor": "start|middle|end", "bold": true, "key": "proy_nombre", "rot": 0}
  {"id": "e04", "kind": "symbol", "group": "line", "svg": "<circle .../>", "dx": 0, "dy": 0}                 a drawing that is moved as a whole; `{pen}` in it is the width
  {"id": "e05", "kind": "logo", "slot": "provider|client", "x": 1, "y": 1, "w": 20, "h": 15, "label": "LOGO EMPRESA", "lx": 10, "ly": 9, "lh": 1.6}
Pure functions: nothing here reads or writes files."""
import math
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from epc_titleblock.errors import TitleblockError

SCHEMA_VERSION = "1.0"
PEN_ROLES = ("cut", "frame", "zone", "outline", "cell", "fine")
DEFAULT_PENS = {"cut": 0.1, "frame": 1.0, "zone": 0.5, "outline": 0.8, "cell": 0.4, "fine": 0.2}
DEFAULT_TEXT = {"coordinates": 3.5, "block": 2.0}
DEFAULT_BLOCK = {"width": 175, "height": 51, "modifications_height": 21.5}
KINDS = ("line", "rect", "text", "symbol", "logo")
GROUPS = ("line", "txt", "var", "rojo")
ANCHORS = ("start", "middle", "end")
SLOTS = ("provider", "client")
MAX_ELEMENTS = 600
SYMBOL_TAGS = ("polygon", "polyline", "circle", "ellipse", "line", "rect", "path", "g")
SYMBOL_ATTRS = ("points", "cx", "cy", "r", "rx", "ry", "x", "y", "x1", "y1", "x2", "y2", "width", "height", "d", "fill", "stroke", "stroke-width", "transform")
BOLD = re.compile(r'</?tspan(?: font-weight="bold")?>')
ENTITIES = re.compile(r"&(?:amp|lt|gt|quot|apos|#\d+);")
MAX_TEXT = 240
RANGES = {"frame.margin_left": (0.0, 60.0), "frame.margin": (0.0, 60.0), "frame.strip": (0.0, 12.0), "pens": (0.05, 3.0), "text.coordinates": (1.0, 12.0), "text.block": (0.8, 10.0),
          "block.width": (60.0, 400.0), "block.height": (20.0, 160.0), "block.modifications_height": (5.0, 100.0)}


def _num(v: Any) -> Optional[float]:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None


def _in(name: str, v: Any, errors: Dict[str, str], key: Optional[str] = None) -> None:
    lo, hi = RANGES[key or name]
    n = _num(v)
    if n is None or not lo <= n <= hi:
        errors[name] = f"a number from {lo:g} to {hi:g} mm"


def _section(config: dict, name: str, allowed, errors: Dict[str, str]) -> dict:
    given = config.get(name)
    if given is None:
        return {}
    if not isinstance(given, dict):
        errors[name] = "an object"
        return {}
    for k in given:
        if k not in allowed:
            errors[f"{name}.{k}"] = "unknown: " + ", ".join(allowed)
    return given


NUMBERS = {"line": ("x1", "y1", "x2", "y2"), "rect": ("x", "y", "w", "h"), "text": ("x", "y", "h"), "symbol": ("dx", "dy"), "logo": ("x", "y", "w", "h")}


def _measure_errors(where: str, e: dict) -> Dict[str, str]:
    """The numbers of an element: where it is and how big, in mm."""
    errors: Dict[str, str] = {}
    for k in NUMBERS[e["kind"]]:
        n = _num(e.get(k, 0 if e["kind"] == "symbol" else None))
        if n is None or abs(n) > 1000:
            errors[f"{where}.{k}"] = "a number in mm"
        elif k in ("h", "w") and e["kind"] in ("rect", "logo") and n <= 0:
            errors[f"{where}.{k}"] = "more than 0"
    return errors


def _element_errors(i: int, e: Any, width: float, height: float, seen: set) -> Dict[str, str]:
    where = f"block.elements[{i}]"
    if not isinstance(e, dict) or e.get("kind") not in KINDS:
        return {where: "an object with a kind: " + ", ".join(KINDS)}
    errors: Dict[str, str] = {}
    eid = e.get("id")
    if not isinstance(eid, str) or not eid.strip() or len(eid) > 24 or eid in seen:
        errors[f"{where}.id"] = "a short text, different for each element"
    seen.add(eid)
    return {**errors, **_measure_errors(where, e), **_element_kind_errors(where, e)}


def markup_ok(text: str) -> bool:
    """A text of the title block is plain, with the entities of XML and, as only markup, the bold part (`<tspan font-weight="bold">CUIT:</tspan> {empresa_cuit}`)."""
    bare = ENTITIES.sub("", BOLD.sub("", text))
    return "<" not in bare and "&" not in bare and bare.count("{") == bare.count("}")


def symbol_ok(markup: str) -> bool:
    """A symbol is drawing only: shapes with their geometry and widths, nothing that runs, loads or links."""
    try:
        root = ET.fromstring("<g>" + markup.replace("{pen}", "0.2") + "</g>")
    except ET.ParseError:
        return False
    return all(el.tag in SYMBOL_TAGS and all(k in SYMBOL_ATTRS for k in el.attrib) for el in root.iter())


def _stroke_errors(where: str, e: dict) -> Dict[str, str]:
    """A line or a rectangle: the role of its pen and, when it has its own, its width (`w` of a line, `lw` of a rectangle)."""
    errors: Dict[str, str] = {}
    if e.get("pen") is not None and e["pen"] not in PEN_ROLES:
        errors[f"{where}.pen"] = "one of " + ", ".join(PEN_ROLES)
    key = "w" if e["kind"] == "line" else "lw"
    own = _num(e.get(key))
    if e.get(key) is not None and not (own is not None and 0.05 <= own <= 3.0):
        errors[f"{where}.{key}"] = "a width from 0,05 to 3 mm"
    return errors


def _text_errors(where: str, e: dict) -> Dict[str, str]:
    errors: Dict[str, str] = {}
    text = e.get("text", "")
    if not isinstance(text, str) or len(text) > MAX_TEXT:
        errors[f"{where}.text"] = f"a text of up to {MAX_TEXT} characters"
    elif not markup_ok(text):
        errors[f"{where}.text"] = "plain text: write &amp; for &, &lt; for <; the only markup allowed is the bold part"
    if not 0.5 <= (_num(e.get("h")) or 0) <= 20:
        errors[f"{where}.h"] = "a text height from 0,5 to 20 mm"
    if e.get("anchor", "start") not in ANCHORS:
        errors[f"{where}.anchor"] = "one of " + ", ".join(ANCHORS)
    return errors


def _logo_errors(where: str, e: dict) -> Dict[str, str]:
    errors: Dict[str, str] = {}
    if not isinstance(e.get("label", ""), str):
        errors[f"{where}.label"] = "a text"
    if e.get("slot") not in SLOTS:
        errors[f"{where}.slot"] = "one of " + ", ".join(SLOTS)
    return errors


def _symbol_errors(where: str, e: dict) -> Dict[str, str]:
    if not isinstance(e.get("svg"), str) or len(e["svg"]) > 2000 or not symbol_ok(e["svg"]):
        return {f"{where}.svg": "shapes only (polygon, polyline, circle, ellipse, line, rect, path) with their geometry and widths, up to 2000 characters"}
    return {}


def _element_kind_errors(where: str, e: dict) -> Dict[str, str]:
    kind = e["kind"]
    errors = {"line": _stroke_errors, "rect": _stroke_errors, "text": _text_errors, "symbol": _symbol_errors, "logo": _logo_errors}[kind](where, e)
    if kind != "logo" and e.get("group", "var" if kind == "text" else "line") not in GROUPS:
        errors[f"{where}.group"] = "one of " + ", ".join(GROUPS)
    return errors


def validate(config: Optional[dict]) -> Dict[str, str]:
    """What is wrong with a configuration, field by field (empty when it is fine)."""
    errors: Dict[str, str] = {}
    if config is None:
        return errors
    if not isinstance(config, dict):
        return {"config": "an object"}
    for k in config:
        if k not in ("schema_version", "format", "frame", "pens", "text", "block"):
            errors[k] = "unknown"
    for name, allowed in (("frame", ("margin_left", "margin", "strip")), ("text", ("coordinates", "block"))):
        for k, v in _section(config, name, allowed, errors).items():
            if k in allowed:
                _in(f"{name}.{k}", v, errors)
    for k, v in _section(config, "pens", PEN_ROLES, errors).items():
        if k in PEN_ROLES:
            _in(f"pens.{k}", v, errors, "pens")
    block = _section(config, "block", ("width", "height", "modifications_height", "elements"), errors)
    for k in ("width", "height", "modifications_height"):
        if k in block:
            _in(f"block.{k}", block[k], errors)
    elements = block.get("elements")
    if elements is not None:
        if not isinstance(elements, list) or len(elements) > MAX_ELEMENTS:
            errors["block.elements"] = f"a list of up to {MAX_ELEMENTS} elements"
        else:
            seen: set = set()
            for i, e in enumerate(elements):
                errors.update(_element_errors(i, e, block.get("width", 175.0), block.get("height", 51.0), seen))
    return errors


def resolve(config: Optional[dict], default_frame: Dict[str, float]) -> Dict[str, Any]:
    """The configuration with everything it did not say filled in from the standard; `default_frame` is that of the format."""
    c = config or {}
    block = c.get("block") or {}
    return {"frame": {**default_frame, **(c.get("frame") or {})}, "pens": {**DEFAULT_PENS, **(c.get("pens") or {})}, "text": {**DEFAULT_TEXT, **(c.get("text") or {})},
            "block": {**DEFAULT_BLOCK, **{k: v for k, v in block.items() if k != "elements"}, "elements": block.get("elements")}}


def prepare(config: Optional[dict], default_frame: Dict[str, float]) -> Dict[str, Any]:
    """The configuration checked and with what it did not say filled in from the standard; raises TitleblockError (what is wrong, field by field) when it is not valid."""
    errors = validate(config)
    if errors:
        raise TitleblockError("err_config_invalid", details="; ".join(f"{k}: {v}" for k, v in errors.items()))
    return resolve(config, default_frame)


def pen_width(element: dict, pens: Dict[str, float], role: str) -> float:
    """The width in mm of an element: its own, else that of its role, else the role the standard gives it."""
    own = element.get("w") if element.get("kind") == "line" else element.get("lw")
    return float(own) if own is not None else pens[element.get("pen") or role]
