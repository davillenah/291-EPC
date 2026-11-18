# ADR-0036: Photovoltaic engine (`epc_pv`)

Status: accepted. Date: 2026-11-14. Follows the pattern of ADR-0029, ADR-0031 and ADR-0033: an engine that calculates, with the norm giving data and the engine giving algorithms.

## Context
The platform sizes the low-voltage side of an installation but has no photovoltaic calculation: the only solar data in the repository are the typical window gains of `epc_hvac`. The owner asked on 2026-11-13 for a photovoltaic engine. pvlib (BSD-3-Clause) was the natural candidate, but it needs Python 3.11 or later and brings numpy, pandas, scipy, h5py, pytz and requests, which would make the local installer much larger; every other calculation engine uses only the standard library.

## Decisions
1. **A standalone engine `epc_pv`** (pure Python, no dependencies): sun position, plane-of-array irradiance, cell temperature, DC and AC power with losses and inverter clipping, and the string layout against the inverter limits. Output: energy per array and in total (annual and monthly), specific yield, performance ratio, capacity factor, clipping, and the strings.
2. **pvlib is the reference of the validation, not a dependency.** `tests/validation/make_reference.py` (developer tool) writes `reference.json` once; the tests compare the engine with it. The owner's criterion is 99.98 %: 1000 different projects of large size, each within 0.02 % of pvlib in annual energy, with identical layouts. A first measurement of the simpler sun position against NREL SPA gave less than 0.01 %. If the criterion cannot be met, the fallback is to depend on pvlib.
3. **The weather is an input.** The engine never reads the network. The Argentine table (PVGIS typical-year data) is a separate data step: PVGIS is a free service of the European Commission JRC whose data may be reused with the source cited; it is fetched on a machine with access and stored with its source and edition, as `pending review`.
4. **Typical values are pending review.** Losses, thermal model, inverter curve, incidence modifier and the short-circuit factor live in `data/params.json` and are indexed in the norm register as `pending`; the result carries a warning until the owner confirms them (D21).
5. **Every user-visible text is in English and Spanish** (`messages.py`): warnings, errors and labels. English is the source.
6. **It sits in the independent engine layer** next to `epc_hvac` (gate suite `engine-pv`, coverage floor, impact map). **Connecting it to the pipeline is a later step**: an optional slice of the calculation stages driven by a `pv` section of `engine_inputs`, like `hvac`.

## Consequences
- A new engine area: gate suite `engine-pv`, coverage floor and impact map.
- Version 1 covers production and strings. DC cables, protections and the connection to the board (with `epc_aea90364`) are the next step.
- Known limits: no shading, bifacial gain, trackers, degradation by year or batteries; the Perez model is not included.
- The comparison with pvlib proves the engine calculates what pvlib calculates with the same models; it does not prove agreement with a real plant.
