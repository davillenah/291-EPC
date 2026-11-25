"""The deliverable service: a drawing hands over its SVG in development and gets back the DXF.

Whoever draws (the single-line, the multi-line, any plan) does not know DXF. It says "here is my SVG, make it a deliverable": symbols that have a DXF block become INSERTs, the strokes are
converted, every entity goes to the layer of its role (`data-layer` in the SVG) as the catalog of layers names it, and colour and line weight follow the SVG.
"""
import hashlib
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import ezdxf

from epc_dxf import layers as _L
from epc_dxf import svg_to_dxf
from epc_dxf import stamp as _stamp


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prepare(text: str, symbol_library) -> tuple:
    """The SVG the converter reads (without the symbols that go as blocks), kept in memory, and those symbols."""
    from epc_dxf import bloques_dxf
    stripped, instances = bloques_dxf.separar(text, symbol_library) if symbol_library else (text, [])
    return svg_to_dxf.SvgText(stripped), instances


def _finish(doc, svg, instances: list, symbol_library, height_mm: float, catalog: Dict[str, dict], a3: Optional[bool], stamp=None) -> tuple:
    """(symbols inserted as blocks, entities per layer). Layers, colours and symbol blocks on the converted drawing: the three steps work on that one document, in memory (COD-07)."""
    from epc_dxf import bloques_dxf, capas_dxf
    capas_dxf.aplicar(None, catalog, stamp, doc=doc, write=False)
    capas_dxf.colorear(svg, None, catalog, a3, stamp, doc=doc, write=False)       # colour, line weight and the layer of each entity by its role
    blocks = bloques_dxf.insertar(None, symbol_library, instances, height_mm, catalog, stamp, doc=doc, write=False)[0] if instances else 0
    return blocks, count_entities(doc)[0]


def _retarget(entity, name: str) -> None:
    entity.dxf.layer = name
    for attrib in getattr(entity, "attribs", []):                                   # the attributes of a block reference go with it
        attrib.dxf.layer = name


def _retarget_blocks(doc, final: Dict[str, str]) -> None:
    """What sits inside a block (a tray with its text) follows its role too."""
    for block in doc.blocks:
        for entity in ([] if block.name.startswith("*") else block):
            entity.dxf.layer = final.get(entity.dxf.layer, entity.dxf.layer)


def finish_draft(doc, dxf_path, layers_file=None, stamp_date=None, seed=None) -> dict:
    """A DXF in development (an ezdxf document) whose entities sit on layers named by their ROLE (`plan.ELEC-LUM`) becomes the deliverable: every role layer is renamed
    and given the look the catalog says, the entities follow and the file is saved (with `stamp_date`, an ISO date or datetime, the file carries that date and GUIDs derived from it and `seed`, so the same drawing gives the same bytes). Returns {"dxf": path, "layers": {name: entities}, "blocks": inserts}."""
    catalog = _L.load(layers_file)                                                   # a path or a list of paths: global, company, project
    drafts = [lay.dxf.name for lay in doc.layers if lay.dxf.name in catalog]
    final = {role: _L.apply(doc, role, catalog) for role in drafts}
    for entity in doc.modelspace():
        if entity.dxf.layer in final:
            _retarget(entity, final[entity.dxf.layer])
    _retarget_blocks(doc, final)
    for role in drafts:
        if final[role] != role:
            doc.layers.remove(role)
    _L.describe_layers(doc, catalog)                                                 # every layer of the file carries its description
    Path(dxf_path).parent.mkdir(parents=True, exist_ok=True)
    _stamp.save(doc, str(dxf_path), _stamp.parse(stamp_date, seed if seed is not None else Path(dxf_path).stem))
    layers, blocks = count_entities(doc)                       # the document that was just written: no need to read the file again
    return {"dxf": str(dxf_path), "layers": layers, "blocks": blocks}


def count_entities(doc) -> tuple:
    """(entities per layer, symbols inserted as blocks) of the model space of a drawing already in memory."""
    counts: Dict[str, int] = {}
    blocks = 0
    for e in doc.modelspace():
        counts[e.dxf.layer] = counts.get(e.dxf.layer, 0) + 1
        blocks += e.dxftype() == "INSERT"
    return dict(sorted(counts.items())), blocks


def inspect(dxf: Path) -> tuple:
    """(entities per layer, symbols inserted as blocks) of the model space of a DXF file."""
    return count_entities(ezdxf.readfile(str(dxf)))


def layers_used(dxf: Path) -> Dict[str, int]:
    """How many entities each layer of the DXF holds (the model space)."""
    return inspect(dxf)[0]


def convert_document(svg_text: str, *, symbol_library=None, layers_file=None, a3: Optional[bool] = None, stamp_date=None, seed: str = "drawing") -> dict:
    """SVG in development -> DXF deliverable, all in memory: nothing is read from or written to a folder except the symbol library the caller names.
    Returns {"doc": the ezdxf document, "stamp": the stamp to save it with, "blocks": ..., "layers": ..., "messages": [...]}."""
    catalog = _L.load(layers_file)
    stamp = _stamp.parse(stamp_date, seed)
    svg, instances = _prepare(svg_text, symbol_library)
    doc = _stamp.reload(svg_to_dxf.convertir(svg, stamp), stamp)      # as the file that was saved and read again
    height = float(re.search(r'height="([\d.]+)mm"', svg_text).group(1)) if instances else 0.0
    blocks, layers = _finish(doc, svg, instances, symbol_library, height, catalog, a3, stamp)
    return {"doc": doc, "stamp": stamp, "blocks": blocks, "layers": layers}


def convert_bytes(svg_text: str, **options) -> dict:
    """Like `convert_document`, with the file as data: {"dxf": bytes, "blocks": ..., "layers": ..., "messages": [...]}. The caller writes the bytes where it wants (ADR-0042)."""
    made = convert_document(svg_text, **options)
    seed = options.get("seed", "drawing")
    blocks = made["blocks"]
    return {"dxf": _stamp.to_text(made["doc"], made["stamp"]).encode(made["doc"].output_encoding or "utf-8"), "blocks": blocks, "layers": made["layers"],
            "messages": [f"DXF {seed}: {blocks} símbolos como bloques"] if blocks else []}


def convert(svg_path, dxf_path=None, *, symbol_library=None, layers_file=None, a3: Optional[bool] = None, stamp_date=None, seed=None) -> dict:
    """SVG in development -> DXF deliverable. Returns {"dxf": path or None, "blocks": symbols inserted as blocks, "layers": {name: entities}, "messages": [...]}.
    `symbol_library` is the folder with the DXF blocks of the symbols (the SVG keeps those it does not know as strokes); `layers_file` an extra catalog that wins over the global one.
    `stamp_date` (optional, ISO date or datetime) makes the file reproducible: creation and update times are that date and the GUIDs are derived from it and `seed` (default: the
    name of the SVG), so the same drawing and date give the same bytes. Without it the file is stamped with the clock and random GUIDs, as ezdxf does."""
    svg = Path(svg_path)
    dxf = Path(dxf_path) if dxf_path else svg.with_suffix(".dxf")
    made = convert_document(svg.read_text(encoding="utf-8"), symbol_library=symbol_library, layers_file=layers_file, a3=a3, stamp_date=stamp_date, seed=svg.stem if seed is None else seed)
    tmp_dxf = svg.with_name(svg.stem + "_trazos.dxf")
    try:
        _stamp.save(made["doc"], str(tmp_dxf), made["stamp"])
        os.replace(tmp_dxf, dxf)
    except PermissionError:
        return {"dxf": None, "blocks": 0, "layers": {}, "messages": [f"AVISO no se pudo escribir {dxf.name}: está abierto en otro programa (cerrarlo y volver a generar)"]}
    blocks = made["blocks"]
    msgs: List[str] = [f"DXF {svg.stem}: {blocks} símbolos como bloques"] if blocks else []
    return {"dxf": str(dxf), "blocks": blocks, "layers": made["layers"], "messages": msgs}
