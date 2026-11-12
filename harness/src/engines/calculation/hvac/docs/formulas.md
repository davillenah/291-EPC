# Formulas of epc_hvac

Units: W, m, m², L/s, K, kg water / kg dry air. Each one is in `src/epc_hvac/loads.py`.

| Heat flow | Formula | Module function |
|---|---|---|
| Conduction | Q = U · A · ΔT | `conduction_w` |
| Solar through a window | Q = A · SHGC · I (I: peak irradiance by orientation) | `solar_w` |
| People | Q = n · (sensible + latent per person) | `people_w` |
| Lighting, equipment | Q = w/m² · A · use factor | `internal_w` |
| Air, sensible | Q = 1.23 · V̇ · Δt | `air_w` |
| Air, latent | Q = 3010 · V̇ · Δw | `air_w` |
| Infiltration | V̇ = ach · V / 3.6 | `infiltration_ls` |
| Ventilation | V̇ = n · per-person rate + A · per-m² rate | `ventilation_ls` |
| Supply air | V̇ = Q_sensible / (1.23 · Δt_supply) | `supply_flow_ls` |
| Refrigeration ton | 1 TR = 3516.85 W | `refrigeration_tons` |

The coefficients 1.23 W·s/(L·K) and 3010 W·s/(L) are the sensible and latent heat of standard air at sea level.

## Sources and status
The physical constants above are standard. The typical values (irradiance, heat of people, ventilation rates, infiltration, use factors) are in `params.json` and `data/ventilation.json`: they are **typical values to confirm**, not copies of a table of a standard.

## Discrepancies
None recorded yet; nothing has been checked against a worked example of the standard.
