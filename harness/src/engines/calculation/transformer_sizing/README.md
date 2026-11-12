# epc_transformer_sizing

Status: **in development**

Calculation engine (MIG-39a, PRD section 12 stage 6, "Supply and transformer sizing"): sizes one supply transformer from a demand in kVA. Pure functions (standard library plus `epc_short_circuit`). It has tests, but stays `in development` because the inputs of stage 6 are partial: the board total kVA is an input, the engines do not produce it yet. Its outputs are drafts (D21).

## Public API
- `rated_current_a(sn_kva, un_v)`: In = Sn / (sqrt(3) x Un) in A. Wraps `epc_short_circuit.short_circuit.corriente_asignada_trafo` (which takes VA).
- `required_apparent_power_kva(demand_kva, reserve_pct)`: demand x (1 + reserve / 100). `reserve_pct` is required (no default: the owner has not decided a growth/reserve criterion) and must be >= 0.
- `select_rating(required_kva, series=None)`: the smallest rating of the series that is >= `required_kva`. Above the largest rating it raises `ValueError` ("no single unit; paralleling not modelled").
- `loading_pct(demand_kva, rating_kva)`: demand / rating x 100.
- `size_transformer(demand_kva, un_secondary_v, reserve_pct, series=None)`: dict with `rating_kva`, `required_kva`, `loading_pct`, `rated_current_a`, `series_used`, `assumptions` and `norm_records`.
- `standard_ratings_kva()`, `clear_cache()`: the series accessor (read lazily, cached).

## Data and provenance
`data/standard_ratings.json`: the commonly published preferred distribution-transformer series (25 ... 2500 kVA). Provenance: convention; no clause located. Review status: **pending review**: values to be verified by the owner against the supply authority / manufacturer catalog. Recorded in `norm_register/params.json` (`transformer_sizing.params.standard_ratings`, status pending). Nothing here is verified.

## Not modelled
Impedance (uk %), losses, short-circuit contribution, load and no-load figures, paralleling of units, temperature or altitude derating, overload capacity and any growth/reserve criterion (the caller gives the reserve).

## Depends on
`epc_short_circuit` (and through it `epc_calc_common`). It never imports a discipline, the platform or the web.

## Tests
`python -m unittest discover -s tests` from this folder (every engine `src/` on `PYTHONPATH`, as the gate does).
