"""One typeface for every DXF of a transmittal (SIM-11), and no layer renaming (DRW-01 stage 3).

The layers of every drawing already carry their final names: the catalog `harness/config/dxf/layers.json` holds the NCS / AIA names (`291-<discipline>-<major>-<minor>-<status>`, or `0-...` for what is outside the standard), so nothing is renamed at the end of a run.
`unify(path)` only rewrites a DXF so that every text style uses the typeface of `config/dxf/text.json` (Arial by default, bold where the style is bold). Colours, line types, layer names and every entity are kept.
"""
from pathlib import Path

from epc_dxf import textstyle



def new_layer_name(name):
    """The layer name at the end of a run: the same one. Kept so that callers of the old renaming keep working; the catalog holds the final names."""
    return name


def _fix_fonts(doc):
    font = textstyle.get_section("font")
    for style in doc.styles:
        bold = "bd" in (style.dxf.font or "").lower() or "bold" in (style.dxf.font or "").lower()
        style.dxf.font = font["bold"] if bold else font["regular"]


def unify(path, stamp_date=None):
    """Rewrites the DXF `path` in place; returns {} (no layer is renamed: the catalog holds the final names). With `stamp_date` the file is written with the pinned times and GUIDs of `epc_dxf.stamp` (the same input gives the same bytes)."""
    import ezdxf
    from epc_dxf import stamp
    path = Path(path)
    doc = ezdxf.readfile(str(path))
    _fix_fonts(doc)
    stamp.save(doc, str(path), stamp.parse(stamp_date, path.stem))
    return {}
