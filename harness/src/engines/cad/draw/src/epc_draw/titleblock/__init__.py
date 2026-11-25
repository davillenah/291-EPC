"""IRAM A0-A4 sheets and custom title blocks (SVG, DXF)."""
__version__ = "0.1.0"

__all__ = ["Logo", "Pluma", "RequestError", "TitleblockError", "build", "main", "project_request", "render", "standard_config", "text_of", "validate", "write"]


def __getattr__(name):
    """The public names load on first use (PEP 562), so importing the package stays as cheap as it was."""
    if name in __all__:
        from epc_draw.titleblock import api
        return getattr(api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
