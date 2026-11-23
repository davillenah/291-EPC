"""epc_grounding: earthing: earth resistance, protective conductors, disconnection times and fault loops (split from epc_aea90364 in MIG-37b)."""
__version__ = "0.1.0"

__all__ = ["GroundingError", "ra_maxima", "resistance_conductor_horizontal", "resistance_parallel", "resistance_rod", "resistencia_malla", "resistencia_placa_circular", "seccion_equipotencial_principal_mm2", "seccion_pe_mm2", "tiempo_desconexion_max_s", "tiempo_seccional_max_s", "verifica_ra", "zs_lazo", "zs_maxima"]


def __getattr__(name):
    """The public names load on first use (PEP 562), so importing the package stays as cheap as it was."""
    if name in __all__:
        from epc_grounding import api
        return getattr(api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
