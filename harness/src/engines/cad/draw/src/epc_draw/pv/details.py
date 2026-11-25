"""The detail drawing of the PV equipment of a run: module (front and edge view), inverter (front and underside view) and the section of the mounting post, drawn from the equipment records.

Every dimension is read from a record (`epc_pv/data`, handed in by the caller): the module outline, the frame width, the cell grid and the junction box; the inverter enclosure and the position of its terminals, display and
switch; the post profile of the structure. What a record does not give is drawn with a reference value on the `pv.DETAIL_REF` layer, and the sheet says so; nothing is calculated. Units: millimetres.

  write(parts, out_dir, name, language, stamp_date) -> path | None      `<name>_equipment_detail.dxf`; None when there is no record to draw
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from epc_draw.pv import parts as pv_parts
from epc_draw.pv.diagrams import Pen, _layers, _new_doc

TEXT = {
    "title": {"en": "PV EQUIPMENT DETAIL", "es": "DETALLE DEL EQUIPAMIENTO FOTOVOLTAICO"},
    "module": {"en": "MODULE", "es": "MÓDULO"},
    "front": {"en": "front view", "es": "vista frontal"},
    "edge": {"en": "edge view", "es": "vista de canto"},
    "under": {"en": "underside view", "es": "vista inferior"},
    "inverter": {"en": "INVERTER", "es": "INVERSOR"},
    "post": {"en": "POST SECTION", "es": "SECCIÓN DEL POSTE"},
    "cells": {"en": "cells", "es": "celdas"},
    "jbox": {"en": "junction box", "es": "caja de conexiones"},
    "frame": {"en": "frame", "es": "marco"},
    "reference": {"en": "REFERENCE GEOMETRY: dimensions from unverified records; pink layer = reference value, not in the record", "es": "GEOMETRÍA DE REFERENCIA: medidas de registros sin verificar; capa rosa = valor de referencia, no está en el registro"},
}
GAP = 1.0   # blank between views, in text heights


def _t(key: str, language: str) -> str:
    return TEXT[key]["es" if language == "es" else "en"]


def _role(layer: str) -> str:
    """The drawing role of a 3D reference layer: reference values go to `pv.DETAIL_REF`, sourced ones to `pv.DETAIL`."""
    return "pv.DETAIL_REF" if layer == pv_parts.FALLBACK_LAYER else "pv.DETAIL"


def _module(pen: Pen, record: Dict[str, Any], ox: float, language: str) -> float:
    """Front and edge views of the module; returns the x where the next block starts."""
    size = (record.get("geometry") or {}).get("module_dimensions_mm") or [0, 0, 0]
    length, width, thick = (float(v) for v in size[:3])
    fw, fl = (v * (1000.0 if i == 0 else 1) for i, v in enumerate(pv_parts.frame_width(record)))
    (jl, jw, jt), jlayer = pv_parts.junction_size(record)
    jl, jw, jt = jl * 1000, jw * 1000, jt * 1000
    pen.text("pv.DETAIL_DIM", f"{_t('module', language)} {record['id']}", ox, length + pen.h * 3, 1.0)
    pen.text("pv.DETAIL_DIM", f"{_t('front', language)}: {length:g} x {width:g} mm", ox, length + pen.h * 1.2, 0.7)
    pen.rect("pv.DETAIL", ox, 0, width, length)
    pen.rect(_role(fl), ox + fw, fw, width - 2 * fw, length - 2 * fw)
    pen.text("pv.DETAIL_DIM", f"{_t('frame', language)} {fw:g} mm", ox + width + pen.h, length - fw, 0.5)
    grid = pv_parts.cell_grid(record)
    if grid:
        cols, rows = grid
        gu, gs = (width - 2 * fw) / cols, (length - 2 * fw) / rows
        for r in range(rows):
            for c in range(cols):
                pen.rect("pv.DETAIL", ox + fw + c * gu + 2, fw + r * gs + 2, gu - 4, gs - 4)
        pen.text("pv.DETAIL_DIM", f"{cols * rows} {_t('cells', language)}", ox + width + pen.h, length / 2, 0.5)
    pen.rect(_role(jlayer), ox + width / 2 - jw / 2, length - fw - jl - 50, jw, jl)
    pen.text("pv.DETAIL_DIM", _t("jbox", language), ox + width + pen.h, length - fw - jl, 0.5)
    ex = ox + width + pen.h * 9
    pen.text("pv.DETAIL_DIM", f"{_t('edge', language)}: {thick:g} mm", ex, length + pen.h * 1.2, 0.7)
    pen.rect("pv.DETAIL", ex, 0, thick, length)
    pen.rect(_role(jlayer), ex - jt, length - fw - jl - 50, jt, jl)
    return ex + thick + pen.h * 8


def _enclosure(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return next((e for e in (record.get("geometry") or {}).get("elements", []) if e.get("kind") in pv_parts.ENCLOSURES and e.get("size_mm")), None)


def _inverter(pen: Pen, record: Dict[str, Any], ox: float, language: str) -> float:
    """Front view (display, indicators, DC switch) and underside view (terminals) of an inverter; returns the x where the next block starts."""
    el = _enclosure(record)
    if el is None:
        return ox
    w, h, d = (float(v) for v in el["size_mm"])
    pen.text("pv.DETAIL_DIM", f"{_t('inverter', language)} {record['id']}", ox, h + pen.h * 3, 1.0)
    pen.text("pv.DETAIL_DIM", f"{_t('front', language)}: {w:g} x {h:g} x {d:g} mm", ox, h + pen.h * 1.2, 0.7)
    pen.rect("pv.DETAIL", ox, 0, w, h)
    ux = ox + w + pen.h * 6
    pen.text("pv.DETAIL_DIM", f"{_t('under', language)}", ux, h + pen.h * 1.2, 0.7)
    pen.rect("pv.DETAIL", ux, 0, w, d)
    for e in record["geometry"]["elements"]:
        if not e.get("size_mm") or e.get("kind") in pv_parts.ENCLOSURES:
            continue
        x, y, z = (float(v) for v in e.get("position_mm", (0, 0, 0)))
        sx, sy, sz = (float(v) for v in e["size_mm"])
        if e["kind"] in pv_parts.CONNECTORS:
            pen.rect("pv.DETAIL", ux + x, d - z - sz / 2, sx, sz)
            pen.text("pv.DETAIL_DIM", e["kind"], ux + x, d - z - sz / 2 - pen.h * 0.7, 0.35)
        elif e["kind"] in pv_parts.FRONT_PARTS:
            pen.rect("pv.DETAIL", ox + x, y, sx, max(sy, 4.0))
    return ux + w + pen.h * 8


def _post(pen: Pen, structure: Dict[str, Any], ox: float, language: str) -> float:
    section = pv_parts.post_section(structure)
    if section is None:
        return ox
    pts = [(x * 1000, y * 1000) for poly in section["polygons"] for x, y in poly]
    x0, x1, y0, y1 = min(p[0] for p in pts), max(p[0] for p in pts), min(p[1] for p in pts), max(p[1] for p in pts)
    pen.text("pv.DETAIL_DIM", f"{_t('post', language)} {structure['id']} ({section['profile']})", ox, y1 - y0 + pen.h * 1.2, 0.7)
    pen.text("pv.DETAIL_DIM", f"{x1 - x0:g} x {y1 - y0:g} mm", ox, y1 - y0 + pen.h * 0.2 - pen.h * 2.0, 0.5)
    for poly in section["polygons"]:
        pen.msp.add_lwpolyline([(ox - x0 + x * 1000, y * 1000 - y0) for x, y in poly], close=True, dxfattribs={"layer": "pv.DETAIL"})
    return ox + (x1 - x0) + pen.h * 8


def build(parts: Dict[str, Any], language: str = "en"):
    """The ezdxf document of the detail sheet, or None when `parts` has no module, inverter or post section to draw."""
    module, structure = parts.get("module"), parts.get("structure")
    inverters = {r["id"]: r for r in (parts.get("inverters") or {}).values() if r}
    if module is None and not inverters and pv_parts.post_section(structure) is None:
        return None
    doc, style = _new_doc(4)
    _layers(doc, ("pv.DETAIL", "pv.DETAIL_REF", "pv.DETAIL_DIM"))
    pen = Pen(doc, style, 40.0)
    x = 0.0
    if module is not None:
        x = _module(pen, module, x, language)
    for rec in inverters.values():
        x = _inverter(pen, rec, x, language)
    if structure is not None:
        x = _post(pen, structure, x, language)
    pen.text("pv.DETAIL_DIM", _t("title", language), 0, -pen.h * 3, 1.4)
    pen.text("pv.DETAIL_DIM", _t("reference", language), 0, -pen.h * 5, 0.6)
    return doc


def write(parts: Dict[str, Any], out_dir, name: str, language: str = "en", stamp_date=None) -> Optional[Path]:
    """Writes `<name>_equipment_detail.dxf` under `out_dir`; None when there is nothing to draw."""
    from epc_draw.core import deliverable
    doc = build(parts, language)
    if doc is None:
        return None
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}_equipment_detail.dxf"
    deliverable.finish_draft(doc, path, None, stamp_date, f"{name}_equipment_detail")
    return path
