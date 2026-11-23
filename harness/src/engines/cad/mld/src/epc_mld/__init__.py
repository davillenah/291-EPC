"""Multi-line diagram data and templates (generator pending)."""
__version__ = "0.1.0"

__all__ = ["Generator", "Sheet", "chain_of", "generate", "library_dir", "main", "nxt", "pole_id", "poles_of"]


def __getattr__(name):
    """The public names load on first use (PEP 562), so importing the package stays as cheap as it was."""
    if name in __all__:
        from epc_mld import api
        return getattr(api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
