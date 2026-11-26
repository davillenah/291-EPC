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
| Voltage coefficient of Vmp | V_mp(T) = V_mp,stc (1 + beta_vmp (T - 25)); beta_vmp defaults to beta_voc when not given | `strings.series_range` |
| Horizon elevation | linear interpolation of the profile points around the circle (azimuth 0..360, wraps) | `shading.horizon_elevation_deg` |
| Horizon shading | the direct beam is zero when sun elevation < horizon elevation at the sun azimuth | `shading.direct_factor` |
| Row shadow reach | reach = (l sin b + l cos b tan a' + D tan b) / (tan b + tan a'), tan a' = tan a / cos psi; l slope length, D pitch, a sun elevation, psi = az_sun - az_surface | `shading.row_shaded_fraction` |
| Row shaded fraction | f = clip((reach - D) / (cos b l), 0, 1) of the slope length; direct factor = 1 - f (1 - 1/n_rows); the front row is never shaded | `shading.row_shaded_fraction` |
| Shading loss | loss % = (E_unshaded - E_shaded) / E_unshaded 100, over the year, per array | `pipeline._shading_loss_pct` |
| Near obstacle | the array is sampled on a 4 x 4 grid; each point sends a ray to the sun; sunlit fraction = points whose ray misses every box (slab test) / points | `nearshade.sunlit_fraction` |
| Tracker, ideal rotation | theta = atan2(cos(el) sin(az_sun - az_axis), sin(el)), el sun elevation | `tracker.rotation_deg` |
| Tracker, backtracking | theta_bt = theta - sign(theta) acos(min(1, cos theta / gcr)); clipped to +/- max angle | `tracker.rotation_deg` |
| Tracker surface | tilt and azimuth of the rotated plane from the rotation and the axis azimuth | `tracker.surface` |
| Degradation | E_n = E_1 (1 - d)^n, n = 0..years-1 (year 1 as computed); total = sum E_n | `lifetime.project` |
| Irradiation disk | kWh/m2 (b, g) = sum G_poa(b, g) dt over the weather year; pct = 100 kWh/m2 / max over all planes | `disk.compute` |
| Disk, any plane | bilinear interpolation between the cells; the azimuth wraps at 360 | `disk.pct_at` |
| Abacus bands | declination edges d_k = d_A - k (23.44 / 2) sign, k = 0..4, from the lowest sun path (A) | `abacus._edges` |
| Abacus sun position | sin e = sin lat sin d + cos lat cos d cos H; azimuth as in the sun position | `abacus.sun_xy` |
| Abacus cell | band of d, hour slot ceil(abs(H) / 15), side of the sign of H (afternoon odd, morning even) | `abacus.cell_id` |
| Abacus weight | share of the annual G_poa of the instants inside the cell | `abacus.weights` |
| Abacus loss | loss % = sum(weight % x cover), cover = hidden share of the cell by the profile rounded to 0, 0.25, 0.5, 0.75, 1 | `abacus.compute` |

Temperature of a voltage: V(T) = V_stc (1 + beta (T - 25)). Cold is the design minimum air temperature; hot is the hottest cell temperature of the year.

## Sources and status
The sun position equations are the NOAA solar calculator ones (Meeus, Astronomical Algorithms). Spencer (1971), Hay and Davies, the ASHRAE incidence modifier, the Faiman model (2008) and the PVWatts DC and inverter models (NREL) are public methods; the implementation is written for this repository. The numbers in `data/params.json` are typical values to confirm, not copies of a standard.

## Discrepancies
Against pvlib 0.16.1 with the same models (NREL SPA sun position): the engine's simpler sun position moves the annual energy by less than 0.01 % (measured in the validation). Nothing has been checked against a measured plant.
