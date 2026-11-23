"""epc_feeder_sizing: feeder and circuit conductor sizing: conductor tables, ampacity, selection by section, thermal withstand and route lengths (split from epc_aea90364 in MIG-37b)."""
__version__ = "0.1.0"

__all__ = ["FeederSizingError", "cargar_tabla", "current_corrected", "current_neutral_harmonics", "current_phase_three_phase", "d_desde_thd", "distorsion_d_pct", "factor_harmonics", "factores", "iz", "iz_admisible", "iz_base", "iz_ruta", "k_adiabatico_771", "k_material", "main", "neutral_section", "parametros", "pe_section", "resistencia_cu_ohm_km", "resistencia_ohm_km", "route_warnings", "seccion_comercial_superior", "seccion_minima_mm2", "seccion_pen_minima_mm2", "seccion_valida", "section_min_circuit", "segment_params", "seleccionar_conductor", "temp_conductor", "thd_desde_d", "thd_pct", "tiempo_maximo_s", "total_length", "validate", "verifica_poder_corte", "verificar_i2t", "verify_overload", "volumen_combustible_dm3_m"]


def __getattr__(name):
    """The public names load on first use (PEP 562), so importing the package stays as cheap as it was."""
    if name in __all__:
        from epc_feeder_sizing import api
        return getattr(api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
