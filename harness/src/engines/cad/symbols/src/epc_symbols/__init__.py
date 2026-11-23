"""IEC 60617 symbol library (SVG and DXF blocks) for single-line and multi-line diagrams, LV and MV."""
from pathlib import Path
from epc_symbols.errors import SymbolsError

LIBRARY = Path(__file__).resolve().parent / "library"
KINDS = ("sld-lv-symbol", "sld-mv-symbol", "mld-lv-symbol", "mld-mv-symbol", "ssd-mv-symbol")
PLAN = "plan-symbol"
ARCH = "arch-symbol"     # the architecture plan symbols (SYM-05): furniture, fixtures and openings, 1 unit = 1 cm, see `arch_symbols`     # the electrical-plan symbols (SYM-04): not a catalogue library, see `plan_symbols`


def library_dir(kind: str = "sld-lv-symbol") -> Path:
    """Folder with `_catalog.json` and the symbol files of one library."""
    if kind not in KINDS + (PLAN, ARCH):
        raise SymbolsError("err_unknown_library", kind=kind, kinds=KINDS)
    return LIBRARY / kind
__version__ = "0.1.0"

__all__ = ["AmbiguousSymbol", "SymbolRecord", "SymbolsError", "UnknownSymbol", "dxf_block", "library_dir", "arch_symbols", "list_ids", "plan_symbols", "resolve", "svg_fragment", "terminals"]


def __getattr__(name):
    """The public names load on first use (PEP 562), so importing the package stays as cheap as it was."""
    if name in __all__:
        from epc_symbols import api
        return getattr(api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
