"""epc_short_circuit: short-circuit currents: symmetrical current at a point, decay with distance and the factors of the calculation (split from epc_aea90364 in MIG-37b)."""
__version__ = "0.1.0"

__all__ = ["ShortCircuitError", "aporte_motor", "c_max_desde_tension", "calcular_ik", "constante_aperiodica_s", "constante_tiempo_mu_q", "constantes_tiempo", "corriente_alterna_t", "corriente_asignada_trafo", "corriente_pico", "corrientes_generador", "current_peak_to", "current_steady_to", "current_thermal_equivalent_to", "defecto_tierra_rigido", "delta_i_kmax", "factor_c", "factor_kappa", "factor_kt", "factor_m", "factor_n_generico", "factor_n_simplificado", "factor_q", "ik_aguas_abajo", "ik_barras", "ik_desde_impedancia", "ik_generador", "ik_grupo_conmutador", "ik_trafo_con_red", "impedance_cable", "impedancia_red", "impedancia_transformador", "k_g", "k_gs", "k_gso", "k_s", "k_so", "k_t_general", "k_ts", "k_tso", "kappa_exacto", "motores_baja_tension_despreciables", "motors_contribution_negligible", "motors_negligible", "mu_generador", "reactancia_red_lv_ohm", "reactancia_trafo_ohm", "voltage_internal_rated", "voltage_internal_subtransient"]


def __getattr__(name):
    """The public names load on first use (PEP 562), so importing the package stays as cheap as it was."""
    if name in __all__:
        from epc_short_circuit import api
        return getattr(api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
