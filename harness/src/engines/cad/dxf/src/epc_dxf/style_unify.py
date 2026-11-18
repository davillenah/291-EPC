"""One layer naming and one typeface for every DXF of a transmittal (SIM-11).

The engines name their layers in three ways (`ARQ-/ELEC-/PLAN-*` of the plan engine, `291-*` of the sheets and diagrams, `A-*` of the architecture style `epc_arch/epc_style.json`) and the plans
carry the fonts of the plan engine. `unify(path)` rewrites a DXF so that its layers follow the `<discipline>-<element>` convention of the architecture style (`A-*` architecture and sheet,
`E-*` electrical; the table is `harness/config/dxf/unify.json`) and every text style uses the typeface of `config/dxf/text.json` (Arial by default, bold where the style is bold). Colours, line types and every entity are kept: only names change.
"""
import re
from pathlib import Path

from epc_dxf import textstyle



def new_layer_name(name):
    """The layer name in the unified convention (a name that already follows it, or the layers `0` and `Defpoints`, stay as they are)."""
    names = textstyle.load_file("unify.json")
    if name in names["layer_names"]:
        return names["layer_names"][name]
    elec = re.fullmatch(r"ELEC-(.+)", name)
    if elec:
        return "E-" + names["elec_elements"].get(elec.group(1), elec.group(1))
    arq = re.fullmatch(r"ARQ-(.+)", name)
    if arq:
        return "A-" + arq.group(1)
    sheet = re.fullmatch(r"291-([A-Z])-(.+)", name)
    return f"{sheet.group(1)}-{sheet.group(2)}" if sheet else name


def _entities(doc):
    yield from doc.modelspace()
    for layout in doc.layouts:
        yield from layout
    for block in doc.blocks:
        yield from block


def _rename_layers(doc, renamed):
    for old, new in renamed.items():
        if new not in doc.layers:
            doc.layers.get(old).dxf.name = new


def _move_entities(doc, renamed):
    for entity in _entities(doc):
        if entity.dxf.hasattr("layer") and entity.dxf.layer in renamed:
            entity.dxf.layer = renamed[entity.dxf.layer]


def _drop_old_layers(doc, renamed):
    for old, new in renamed.items():
        if old in doc.layers and new in doc.layers and old != new:
            doc.layers.remove(old)


def _fix_layers(doc):
    renamed = {n: new_layer_name(n) for n in [l.dxf.name for l in doc.layers] if new_layer_name(n) != n}
    _rename_layers(doc, renamed)
    _move_entities(doc, renamed)
    _drop_old_layers(doc, renamed)
    return renamed


def _fix_fonts(doc):
    font = textstyle.get_section("font")
    for style in doc.styles:
        bold = "bd" in (style.dxf.font or "").lower() or "bold" in (style.dxf.font or "").lower()
        style.dxf.font = font["bold"] if bold else font["regular"]


def unify(path, stamp_date=None):
    """Rewrites the DXF `path` in place; returns {old layer: new layer} of the layers it renamed. With `stamp_date` the file is written with the pinned times and GUIDs of `epc_dxf.stamp` (the same input gives the same bytes)."""
    import ezdxf
    from epc_dxf import stamp
    path = Path(path)
    doc = ezdxf.readfile(str(path))
    renamed = _fix_layers(doc)
    _fix_fonts(doc)
    stamp.save(doc, str(path), stamp.parse(stamp_date, path.stem))
    return renamed
