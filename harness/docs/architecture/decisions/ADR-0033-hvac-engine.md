# ADR-0033: HVAC engine (thermal side of the air-conditioning)

Status: accepted. Date: 2026-11-09. Follows the pattern of ADR-0029 and ADR-0031: an engine that calculates, with the norm giving data and the engine giving algorithms.

## Context
The platform already calculates the electrical side of the air-conditioning equipment (circuit, cable, drop and start, `E3-02`). The thermal side (cooling load and air flows) belongs to another discipline with other standards (ASHRAE), so it does not fit inside the electrical engine `epc_aea90364`. The owner asked for a separate engine on 2026-11-09 (`E3-10`).

## Decisions
1. **A standalone engine `epc_hvac`** (pure Python, no dependencies): cooling load per space by the basic method, supply air flow and outdoor air.
2. **The data are typical values to confirm.** Irradiance, heat of people and ventilation rates live in `params.json` and `data/ventilation.json`, marked as unreviewed; the result carries a warning until the owner confirms them. No table of a standard is copied.
3. **It sits in the independent engine layer** next to `epc_plan`, `epc_lighting` and `epc_receptacles` (import-linter layer, gate suite, coverage floor, impact map).
4. **Connection to the platform is a later step** (`E3-15`): inputs per space, the study document and the link with the electrical HVAC study.

## Consequences
- A new engine area: gate suite `engine-hvac`, coverage floor, impact map and import-linter layer.
- The electrical power of the equipment keeps coming from the equipment loaded in the load list; this engine gives the thermal load that should agree with it, and a later check can compare them.
- Heating loads, psychrometrics, duct and coil sizing are out of this first version.
