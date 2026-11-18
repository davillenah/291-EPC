# Formulas of epc_pv

Units: W, W/m2, degrees (angles), degrees C, V, A, kWh. Each one is in `src/epc_pv/`.

| Step | Formula | Function |
|---|---|---|
| Julian day | JD = ordinal + 1721424.5 + minutes/1440 | `solar.julian_day` |
| Declination and equation of time | NOAA series of the Julian century (Meeus, low precision) | `solar._declination_and_eot` |
| Hour angle | H = (UT + EoT + 4 lon) / 4 - 180 | `solar.position` |
| Zenith | cos z = sin lat sin decl + cos lat cos decl cos H | `solar.position` |
| Azimuth (from north, clockwise) | atan2(sin H, cos H sin lat - tan decl cos lat) + 180 | `solar.position` |
| Refraction | NOAA piecewise approximation of the true elevation | `solar.refraction_deg` |
| Extraterrestrial irradiance | I0 (1.00011 + 0.034221 cos G + 0.00128 sin G + 0.000719 cos 2G + 0.000077 sin 2G), G = 2 pi (doy - 1) / 365 | `solar.extra_radiation_w_m2` |
| Angle of incidence | cos aoi = cos z cos b + sin z sin b cos(az_sun - az_surface) | `irradiance.cos_aoi` |
| Direct on the plane | DNI max(cos aoi, 0) | `irradiance.plane_of_array` |
| Ground reflection | albedo GHI (1 - cos b) / 2 | `irradiance.plane_of_array` |
| Sky diffuse, isotropic | DHI (1 + cos b) / 2 | `irradiance.sky_diffuse` |
| Sky diffuse, Hay-Davies | DHI [AI Rb + (1 - AI)(1 + cos b) / 2], AI = DNI / I0, Rb = max(cos aoi, 0) / max(cos z, 0.01745) | `irradiance.sky_diffuse` |
| Incidence modifier (ASHRAE) | max(0, 1 - b0 (1 / cos aoi - 1)) | `irradiance.iam_ashrae` |
| Cell temperature (Faiman) | T_air + G_poa / (u0 + u1 v) | `thermal.faiman_cell_c` |
| DC power (PVWatts) | P_stc (G_eff / 1000) (1 + gamma (T_cell - 25)) | `power.dc_power_w` |
| Combined loss | 1 - product(1 - l_i) | `config.losses_total_pct` |
| Inverter | zeta = P_dc / (P_ac0 / eta_nom); eta = eta_nom / eta_ref (-0.0162 zeta - 0.0059 / zeta + 0.9858); P_ac = min(eta P_dc, P_ac0) | `power.inverter_curve_w`, `power.inverter_ac_w` |
| Strings, upper limit | n_series <= min(Vdc_max / Voc_cold, Vmppt_max / Vmp_cold) | `strings.series_range` |
| Strings, lower limit | n_series >= Vmppt_min / Vmp_hot | `strings.series_range` |
| Strings per input | <= min(I_max / I_mp, I_sc,max / (I_sc k)) | `strings.layout` |

Temperature of a voltage: V(T) = V_stc (1 + beta (T - 25)). Cold is the design minimum air temperature; hot is the hottest cell temperature of the year.

## Sources and status
The sun position equations are the NOAA solar calculator ones (Meeus, Astronomical Algorithms). Spencer (1971), Hay and Davies, the ASHRAE incidence modifier, the Faiman model (2008) and the PVWatts DC and inverter models (NREL) are public methods; the implementation is written for this repository. The numbers in `data/params.json` are typical values to confirm, not copies of a standard.

## Discrepancies
Against pvlib 0.16.1 with the same models (NREL SPA sun position): the engine's simpler sun position moves the annual energy by less than 0.01 % (measured in the validation). Nothing has been checked against a measured plant.
