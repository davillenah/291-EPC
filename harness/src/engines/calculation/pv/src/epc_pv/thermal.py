"""Cell temperature by the Faiman model: T_cell = T_air + G_poa / (u0 + u1 v), with u0 in W/m2/K and u1 in W s/m3/K."""


def faiman_cell_c(poa_w_m2: float, air_c: float, wind_ms: float, u0: float, u1: float) -> float:
    return air_c + poa_w_m2 / (u0 + u1 * wind_ms)
