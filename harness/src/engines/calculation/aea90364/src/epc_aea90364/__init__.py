"""EPC calculation engine: low-voltage electrical sizing per AEA 90364 / IEC 60364 (draft: tables pending validation)."""
__version__ = "1.6.0"

__all__ = ["Aea90364Error", "apply_rows", "balance", "banco", "build", "buscar", "caida_arranque", "calcular_desde_xlsx", "calculate", "circuito_json", "convert_load", "copy_doc", "corriente_arranque", "corriente_proyecto", "current_nominal_equivalent", "current_sc_min", "curve_band", "curve_letter", "dec2", "defaults", "doc_markdown", "dump", "evaluar", "export_calculation", "expression", "factor_demand", "factor_k_circuitos", "factor_k_nivel", "facts", "fp_objetivo_defecto", "frecuencia_tolerable", "group_row", "grupo", "grupos", "head", "head_current", "hz", "impactos_directos_anuales", "indice", "induccion_admisible", "induccion_conductor_t", "leer_xlsx", "limite_arranque_pct", "limpiar_cache_reglas", "load", "load_calculation", "load_input", "load_multiple_complies", "mark", "matches", "memoria_doc", "memoria_md", "mm", "multiplo_arranque", "nivel_proteccion", "ok", "override_of", "p1", "parametros_nivel", "plan", "poder_corte_minimo_diferencial_a", "potencia_disipada_aparato_w", "potencia_disipada_polo_w", "potencia_tablero_w", "proteccion_motor", "radio_zona2_con_tabique_m", "reactiva_a_compensar", "regla", "reglas", "resolve", "resolve_doc", "resolver_criterios", "resolver_instalacion", "sig2", "sintesis_doc", "sintesis_md", "superficie_captacion_m2", "transferencia", "type_circuit", "ups", "validate", "validate_calculation", "valor", "verify_panel", "within_accumulated_limit"]


def __getattr__(name):
    """The public names load on first use (PEP 562), so importing the package stays as cheap as it was."""
    if name in __all__:
        from epc_aea90364 import api
        return getattr(api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
