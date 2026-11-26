"""Places a library symbol in a DXF document as a block reference (INSERT), the way every drawing engine must (PRD-symbols, SYM-01).

The symbol library (`epc_draw.symbols`) depends on nothing, so it only says where a block is: `epc_draw.symbols.registry.dxf_block(id, view)` gives (file, block name) and this module does the DXF part.
"""
from pathlib import Path
from typing import Optional, Tuple


def import_block(doc, dxf_file, block: str) -> None:
    """Imports the definition of `block` from the library file into `doc` unless the document already has it (one definition per document)."""
    import ezdxf
    from ezdxf.addons import importer
    if block in doc.blocks:
        return
    imp = importer.Importer(ezdxf.readfile(str(dxf_file)), doc)
    imp.import_block(block)
    imp.finalize()


def insert(doc, dxf_file, block: str, at: Tuple[float, float], scale: float = 1.0, layer: Optional[str] = None, attribs: Optional[dict] = None):
    """One INSERT of `block` at `at` in the modelspace, with its attributes filled from `attribs` (missing tags stay empty). Returns the INSERT entity."""
    import_block(doc, Path(dxf_file), block)
    extra = {"layer": layer} if layer else {}
    ref = doc.modelspace().add_blockref(block, at, dxfattribs=dict(extra, xscale=scale, yscale=scale, zscale=scale))
    values = attribs or {}
    ref.add_auto_attribs({tag: values.get(tag, "") for tag in (a.dxf.tag for a in doc.blocks.get(block).query("ATTDEF"))})
    return ref
