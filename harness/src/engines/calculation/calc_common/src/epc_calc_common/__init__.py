"""epc_calc_common: shared infrastructure of the calculation engines: the norm-data loader, the norm tables, the protection parameters, argument validation, number formatting and rounding (split from epc_aea90364 in MIG-37b)."""
__version__ = "0.1.0"

__all__ = ["CalcCommonError", "MissingNormDataError", "cargar", "clear_cache", "columnas_de_cargados", "constante", "criteria_file", "d2", "derived", "factor_agrupamiento_aire", "factor_agrupamiento_canos", "factor_agrupamiento_enterrado", "factor_resistividad", "factor_temperatura_aire", "factor_temperatura_suelo", "iz_corregida", "iz_tabla", "k1_no_disparo", "k2_convencional", "k_max_i2_iz", "limpiar_cache_tablas", "load_json", "mm", "normative_dir", "numeric_key", "p1", "path", "read_json", "round_down_2", "round_up_2", "rules_dir", "secciones", "separacion_idx", "sig2", "value"]


def __getattr__(name):
    """The public names load on first use (PEP 562), so importing the package stays as cheap as it was."""
    if name in __all__:
        from epc_calc_common import api
        return getattr(api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
