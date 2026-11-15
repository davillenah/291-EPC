"""DC and AC power.

    DC (PVWatts)   P = P_stc (G_eff / 1000) (1 + gamma (T_cell - 25))         then times (1 - total loss)
    inverter       zeta = P_dc / P_dc0, P_dc0 = P_ac0 / eta_nom
                   eta = eta_nom / eta_ref (-0.0162 zeta - 0.0059 / zeta + 0.9858), P_ac = min(eta P_dc, P_ac0), never below 0
"""
G_STC_W_M2 = 1000.0
T_STC_C = 25.0


def dc_power_w(p_stc_w: float, effective_w_m2: float, cell_c: float, gamma_per_c: float) -> float:
    if effective_w_m2 <= 0.0:
        return 0.0
    return p_stc_w * effective_w_m2 / G_STC_W_M2 * (1.0 + gamma_per_c * (cell_c - T_STC_C))


def inverter_curve_w(pdc_w: float, pac0_w: float, eta_nom: float, eta_ref: float) -> float:
    """AC output of one inverter for the DC power at its input before the rating limit (W, never below 0)."""
    if pdc_w <= 0.0:
        return 0.0
    zeta = pdc_w / (pac0_w / eta_nom)
    return max(0.0, eta_nom / eta_ref * (-0.0162 * zeta - 0.0059 / zeta + 0.9858) * pdc_w)


def inverter_ac_w(pdc_w: float, pac0_w: float, eta_nom: float, eta_ref: float) -> float:
    """AC output of one inverter, limited to its rating."""
    return min(pac0_w, inverter_curve_w(pdc_w, pac0_w, eta_nom, eta_ref))
