"""IEC 60617 symbol library (SVG and DXF blocks) for single-line and multi-line diagrams, LV and MV."""
from pathlib import Path
from epc_symbols.errors import SymbolsError

LIBRARY = Path(__file__).resolve().parent / "library"
KINDS = ("sld-lv-symbol", "sld-mv-symbol", "mld-lv-symbol", "mld-mv-symbol", "ssd-mv-symbol")


def library_dir(kind: str = "sld-lv-symbol") -> Path:
    """Folder with `_catalog.json` and the symbol files of one library."""
    if kind not in KINDS:
        raise SymbolsError("err_unknown_library", kind=kind, kinds=KINDS)
    return LIBRARY / kind
__version__ = "0.1.0"
