"""The formulas of the basic cooling-load method (steady state at the design hour; SI units). Each function is one heat flow in watts.

    conduction   Q = U · A · ΔT
    solar        Q = A · SHGC · I               (I: peak irradiance of the orientation, typical values of `params.json`)
    people       Q = n · (sensible + latent per person)
    lighting     Q = w/m² · A · use factor
    equipment    Q = w/m² · A
    air          sensible Q = 1.23 · V̇ · Δt      latent Q = 3010 · V̇ · Δw      (V̇ in L/s, Δt in K, Δw in kg water / kg dry air)
    supply air   V̇ = Q_sensible / (1.23 · Δt_supply)
"""
from typing import Dict

from epc_hvac import config
from epc_hvac.model import HvacError


def _pos(value, name: str, allow_zero: bool = True) -> float:
    v = float(value)
    if v < 0 or (v == 0 and not allow_zero):
        raise HvacError("err_out_of_range", name=name, relation='>= 0' if allow_zero else '> 0', got=value)
    return v


def conduction_w(u_w_m2k: float, area_m2: float, delta_t_k: float) -> float:
    """Heat through a surface of area `area_m2` and transmittance `u_w_m2k` for a temperature difference (K; negative when it loses heat)."""
    return _pos(u_w_m2k, "u_w_m2k") * _pos(area_m2, "area_m2") * float(delta_t_k)


def solar_w(area_m2: float, shgc: float, orientation: str) -> float:
    """Solar gain of a window: area · solar heat gain coefficient · peak irradiance of its orientation (N, NE, E, SE, S, SW, W, NW or H for a horizontal one)."""
    peak = config.solar_peak_w_m2()
    if orientation not in peak:
        raise HvacError("err_orientation_invalid", allowed=sorted(peak), orientation=orientation)
    if not 0 <= float(shgc) <= 1:
        raise HvacError("err_shgc_range", shgc=shgc)
    return _pos(area_m2, "area_m2") * float(shgc) * peak[orientation]


def people_w(occupants: float) -> Dict[str, float]:
    """Sensible and latent heat of `occupants` persons."""
    p = config.params()
    n = _pos(occupants, "occupants")
    return {"sensible": n * p["person_sensible_w"], "latent": n * p["person_latent_w"]}


def internal_w(area_m2: float, w_m2: float, use_factor: float = 1.0) -> float:
    """Heat of lighting or equipment given per m² of floor."""
    return _pos(area_m2, "area_m2") * _pos(w_m2, "w_m2") * _pos(use_factor, "use_factor")


def air_w(flow_ls: float, delta_t_k: float, delta_w_kgkg: float) -> Dict[str, float]:
    """Sensible and latent heat carried by an outdoor air flow (infiltration or ventilation) in L/s."""
    q = _pos(flow_ls, "flow_ls")
    return {"sensible": config.AIR_SENSIBLE_W_PER_LS_K * q * float(delta_t_k), "latent": config.AIR_LATENT_W_PER_LS_KGKG * q * float(delta_w_kgkg)}


def infiltration_ls(volume_m3: float, ach: float) -> float:
    """Infiltration flow (L/s) of a volume with `ach` air changes per hour."""
    return _pos(volume_m3, "volume_m3") * _pos(ach, "ach") / 3.6


def ventilation_ls(use: str, occupants: float, area_m2: float) -> float:
    """Outdoor air (L/s) a use needs: per person plus per m² of floor."""
    r = config.ventilation_rates(use)
    return _pos(occupants, "occupants") * r["per_person_ls"] + _pos(area_m2, "area_m2") * r["per_m2_ls"]


def supply_flow_ls(sensible_w: float, supply_delta_t_k: float) -> float:
    """Supply air flow (L/s) that removes `sensible_w` with a supply air `supply_delta_t_k` colder than the room."""
    if float(supply_delta_t_k) <= 0:
        raise HvacError("err_supply_delta_t")
    return max(0.0, float(sensible_w)) / (config.AIR_SENSIBLE_W_PER_LS_K * float(supply_delta_t_k))


def refrigeration_tons(total_w: float) -> float:
    """Watts as tons of refrigeration."""
    return float(total_w) / config.WATTS_PER_REFRIGERATION_TON
