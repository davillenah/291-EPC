"""epc_selectivity: protection against indirect contact by supply scheme and coordination of the protective devices (split from epc_aea90364 in MIG-37b)."""
__version__ = "0.1.0"

__all__ = ["SelectivityError", "corriente_falla_tt", "i2_convencional", "in_max_por_iz", "ra_maxima_tt", "verifica_it_segunda_falla", "verifica_tn", "verifica_tt"]


def __getattr__(name):
    """The public names load on first use (PEP 562), so importing the package stays as cheap as it was."""
    if name in __all__:
        from epc_selectivity import api
        return getattr(api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
