# epc_hvac

HVAC engine: the cooling load of each space of a building by the basic ASHRAE method (steady state at the design hour), the supply air flow that removes it and the outdoor air the space needs. Pure Python, no dependencies, deterministic.

## What it does
- Heat flows of a space in watts: conduction through walls, roofs and windows, solar gain of windows, people, lighting, equipment, infiltration and ventilation (sensible and latent).
- Supply air flow (L/s) from the sensible load and the supply temperature difference.
- Outdoor air (L/s) from the use of the space, its occupants and its area.
- Totals in W, kW-equivalent and tons of refrigeration.

## How it is used
```
python -m epc_hvac INPUT.json --out DIR       # writes DIR/hvac_loads.json
```
or `from epc_hvac import run; run(document).as_dict()`. Input and output follow `src/epc_hvac/schema/*.schema.json`; the result carries `schema_version`, `counts` and `warnings`.

## Depends on
Nothing (standard library). The electrical side of the equipment is calculated by `epc_aea90364` (`aea_motor` and the HVAC power study); this engine gives the thermal side.

## Known limits
- **The values are typical and not confirmed** (`data/typical.json`): solar irradiance by orientation, heat of people, ventilation rates per use. The result says so in `warnings`; do not size equipment with it until the owner confirms them on the norms page.
- Basic method: no time delay of the walls (no CLTD or radiant time series), no psychrometric coil selection, no duct sizing, no heating load.
- The formulas are in `docs/formulas.md`.
