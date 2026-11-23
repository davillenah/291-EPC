"""epc_load_balance: load balance: demand and design current of loads and boards, load current, phase balance and the project system voltage (U0) (split from epc_aea90364 in MIG-37b)."""
__version__ = "0.1.0"

__all__ = ["LoadBalanceError", "apparent_kva", "assign_phases", "balance", "balance_cargas", "board_u0", "board_un_v", "board_use_v", "board_voltages", "coef_simultaneidad_conjunto", "coef_simultaneity_770", "coef_simultaneity_771", "corriente_alimentador_motores", "corriente_monofasica", "corriente_trifasica", "current_msd", "default_un_v", "dpms_total", "factor_demanda_sistema", "factor_parallel", "grade_electrification_770", "grade_electrification_771", "imbalance_phases", "msd_circuits", "msd_lighting_general", "potencia_aparente_desde_p", "power_apparent_single_phase", "power_apparent_three_phase", "requiere_trifasico", "reserve_breaker", "split_phases", "system_u0", "systems"]


def __getattr__(name):
    """The public names load on first use (PEP 562), so importing the package stays as cheap as it was."""
    if name in __all__:
        from epc_load_balance import api
        return getattr(api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
