"""One API over the symbol libraries (PRD-symbols, SYM-01).

An engine asks for a symbol by id and view and never opens a symbol file or builds a file name. `resolve` accepts the id of the catalogue (`lv_mccb_basic`),
the qualified id (`electrical-lv.lv_mccb_basic`) and the file name with or without its extension, so the old generators keep working while they migrate.
A symbol that does not exist is an error (`UnknownSymbol`), never a stand-in.
"""
from __future__ import annotations

import functools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from epc_symbols import KINDS, library_dir

# library -> (domain, view)
DOMAINS: Dict[str, Tuple[str, str]] = {
    "sld-lv-symbol": ("electrical-lv", "sld"),
    "mld-lv-symbol": ("electrical-lv", "mld"),
    "sld-mv-symbol": ("electrical-mv", "sld"),
    "mld-mv-symbol": ("electrical-mv", "mld"),
    "ssd-mv-symbol": ("electrical-mv", "ssd"),
}


class UnknownSymbol(KeyError):
    """The symbol is not in the library (or has no block in the requested form). The message carries English and Spanish."""

    def __init__(self, symbol_id: str, view: Optional[str] = None, reason_en: str = "is not in the symbol library", reason_es: str = "no está en la biblioteca de símbolos"):
        where = f" (view {view})" if view else ""
        super().__init__(f"symbol {symbol_id!r}{where} {reason_en} / el símbolo {symbol_id!r}{where} {reason_es}")


class AmbiguousSymbol(ValueError):
    """The id matches symbols of more than one view: say the view."""


@dataclass(frozen=True)
class SymbolRecord:
    id: str                      # qualified: <domain>.<catalogue id>
    catalog_id: str
    domain: str
    view: str
    library: str
    title_en: str
    title_es: str
    size: Tuple[float, float]
    ports: Tuple[dict, ...]
    slots: Tuple[dict, ...]
    svg: Path
    dxf: Optional[Path]

    @property
    def block(self) -> Optional[str]:
        """Name of the block definition inside the DXF file (the file name without its extension)."""
        return self.dxf.stem if self.dxf else None


def _record(kind: str, row: dict) -> SymbolRecord:
    folder = library_dir(kind)
    domain, view = DOMAINS[kind]
    svg = folder / row["file"]
    dxf = svg.with_suffix(".dxf")
    size = row.get("size") or {}
    return SymbolRecord(id=f"{domain}.{row['id']}", catalog_id=row["id"], domain=domain, view=view, library=kind,
                        title_en=row.get("name_en", ""), title_es=row.get("name_es", ""), size=(size.get("w", 0.0), size.get("h", 0.0)),
                        ports=tuple(row.get("ports") or ()), slots=tuple(row.get("label_slots") or ()), svg=svg, dxf=dxf if dxf.is_file() else None)


def _rows(kind: str) -> List[dict]:
    catalog = library_dir(kind) / "_catalog.json"
    return json.loads(catalog.read_text(encoding="utf-8-sig"))["symbols"] if catalog.is_file() else []


@functools.lru_cache(maxsize=1)
def _index() -> Tuple[Tuple[SymbolRecord, ...], Dict[str, Tuple[SymbolRecord, ...]]]:
    records = tuple(_record(kind, row) for kind in KINDS for row in _rows(kind))
    aliases: Dict[str, List[SymbolRecord]] = {}
    for rec in records:
        for key in (rec.id, rec.catalog_id, rec.svg.stem, rec.svg.name):
            aliases.setdefault(key, []).append(rec)
    return records, {key: tuple(found) for key, found in aliases.items()}


def resolve(symbol_id: str, view: Optional[str] = None) -> SymbolRecord:
    """The record of a symbol. `view` ('sld', 'mld', 'ssd') narrows ids that exist in several views."""
    found = [r for r in _index()[1].get(symbol_id, ()) if view in (None, r.view)]
    if not found:
        raise UnknownSymbol(symbol_id, view)
    if len(found) > 1:
        raise AmbiguousSymbol(f"{symbol_id!r} exists in views {sorted(r.view for r in found)}: give the view / existe en varias vistas: indique la vista")
    return found[0]


def list_ids(domain: Optional[str] = None, view: Optional[str] = None) -> List[str]:
    """Qualified ids, sorted, optionally of one domain and/or view."""
    return sorted(r.id for r in _index()[0] if domain in (None, r.domain) and view in (None, r.view))


def terminals(symbol_id: str, view: Optional[str] = None) -> Tuple[dict, ...]:
    """Connection points of a symbol (id, x, y, direction), in the coordinates of its drawing."""
    return resolve(symbol_id, view).ports


def dxf_block(symbol_id: str, view: Optional[str] = None) -> Tuple[Path, str]:
    """(file, block name) of the DXF block of a symbol. Raises UnknownSymbol when the symbol has no block."""
    rec = resolve(symbol_id, view)
    if rec.dxf is None:
        raise UnknownSymbol(symbol_id, view, "has no DXF block", "no tiene bloque DXF")
    return rec.dxf, rec.block


def svg_fragment(symbol_id: str, view: Optional[str] = None):
    """The drawing of a symbol as an ElementTree element: its group `id=<catalogue id>` when the file has one, otherwise the root."""
    from xml.etree import ElementTree
    rec = resolve(symbol_id, view)
    root = ElementTree.parse(rec.svg).getroot()
    return next((el for el in root.iter() if el.get("id") == rec.catalog_id), root)


def plan_symbols() -> Dict[str, dict]:
    """The unit symbols of the electrical plan (SYM-04): id -> {"disciplina", "prims" | "svg", ...}; an `svg` entry is the absolute path of its file.

    A fresh copy each call, so the caller may complete it (for example with the primitives read from the SVG) without changing the library.
    """
    folder = library_dir("plan-symbol")
    data = json.loads((folder / "plan_symbols.json").read_text(encoding="utf-8"))["symbols"]
    for entry in data.values():
        if "svg" in entry:
            entry["svg"] = str(folder / entry["svg"])
    return data


def arch_symbols() -> List[dict]:
    """The symbols of the architecture plan (SYM-05): one record per symbol with `nombre`, `categoria`, `ancho_cm`, `alto_cm`, `descripcion` and `archivo`, the absolute path of its SVG (1 unit = 1 cm)."""
    folder = library_dir("arch-symbol")
    rows = json.loads((folder / "catalogo.json").read_text(encoding="utf-8"))["simbolos"]
    return [{**row, "archivo": str(folder / row["archivo"])} for row in rows]
