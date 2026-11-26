"""Single-line diagram generator for boards (SVG and DXF per sheet)."""
__version__ = "0.1.0"

__all__ = ["SldError", "SldInput", "draw", "draw_files", "main", "paginate"]


def __getattr__(name):
    """The public names load on first use (PEP 562), so importing the package stays as cheap as it was."""
    if name in __all__:
        from epc_draw.sld import api
        return getattr(api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
