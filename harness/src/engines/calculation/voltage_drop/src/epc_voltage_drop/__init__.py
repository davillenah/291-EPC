"""epc_voltage_drop: voltage drop of a circuit by the moment method, limits and maximum length (split from epc_aea90364 in MIG-37b)."""
__version__ = "0.1.0"

__all__ = ["VoltageDropError", "caida_disponible_terminal_pct", "caida_gdc", "caida_tension", "coeficiente_gdc", "complies_limit", "corriente_extremo", "drop_by_table", "drop_unit_table", "drop_voltage_single_phase_v", "drop_voltage_three_phase_v", "limite_caida_pct", "longitud_maxima_gdc", "longitud_maxima_m", "porcentaje", "seccion_minima_gdc", "verify_drop"]


def __getattr__(name):
    """The public names load on first use (PEP 562), so importing the package stays as cheap as it was."""
    if name in __all__:
        from epc_voltage_drop import api
        return getattr(api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
