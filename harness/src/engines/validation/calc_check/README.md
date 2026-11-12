# epc_calc_check

Status: **implemented**

Deterministic verification of what the engines produced, without trusting the stage code that produced it (PRD section 5: the agent that produces a result never verifies it). Pure Python; the only engine it calls is `epc_aea90364` (its low-level functions), and only when a check runs. No I/O at import, no web, no Claude, and it imports nothing from `disciplines` or the platform.

```
import epc_calc_check as C
findings = C.check_run(run_result, project=project, files=files, run_id="run-1")
```

- `run_result`: the JSON form of the discipline `RunResult` (`{"pipeline_run_id", "results": [{"stage", "status", "outputs", "findings", ...}]}`).
- `project` (optional): the engine inputs a recalculation needs, `{"circuits": {tag: {engine row keys}}, "voltage_v", "conductor_temp_c", "manifest_schema"}`. A circuit entry says "these are all the engine inputs"; a key that is absent has the engine's own default. A circuit without an entry is reported as `CC-R00` (not recomputable), never guessed.
- `files` (optional): `{path: bytes | sha256}` of the deliverable files (keyed `<directory>/<path>` as stage 14 lists them) and `*.manifest.json` files.
- `groups` (optional): run only `recalc`, `invariants`, `format`, `documents` or `manifests`; `start_id` continues finding numbering.
- Result: findings that validate against `finding.schema.json` (`F-0001`..., verifier `calc-check`, `format-check` or `document-check`). `clause` is `CC-xxx: <text the engine carries>` for rules that come from a norm criterion and `project criterion CC-xxx` otherwise; no clause number is invented.

## Rules

| Group | Rules |
| --- | --- |
| Recalculation (calc-check) | CC-R00 not recomputable (note), R01 Iz, R02 own voltage drop, R03 PE and neutral, R04 I2, R05 Icu series |
| Invariants (calc-check) | CC-B01 Ib <= In <= Iz, B02 I2 <= k_max Iz, B03 drop verdict, B04 drop limit, B05 Icu >= Icc, B06 busbar Icc, B07 trip, B08 flags, B09 minimum section, B10 accumulated drop, B11 differential, B12 standard series |
| Format (format-check) | CC-F01 run shape, F02 missing key, F03 NaN/inf (blocking), F04 types, F05 duplicates, F06 hashes, F07 units, F08 findings, F09 same circuits, F10 manifest schema, F11 labels, F12 a check could not read the data |
| Documents (document-check) | CC-D01 stages agree, D02 memo cells, D03 document hash, D04 memo summary, D05 drawing summary, D06 file or manifest hash (blocking), D07 not comparable (note) |

The table lives in `src/epc_calc_check/rules.py`; every rule has a seeded-error test in `tests/test_checks.py`.

## Limits

- Recalculation covers Iz, the own voltage drop, PE / neutral, I2 and Icu. A cable with a multi-segment route and Icc min (needs the cumulative impedance of the parent chain) are reported as not recomputable.
- The drop is compared to one unit of its last rounded digit (the engine rounds to 3 decimals and the stage rows carry rounded currents); every other recalculated engine value is compared for exact equality.
- Memo cells are compared after formatting the stage value with the engine's own formatters.

Tests: `python -m unittest discover -s tests` with `PYTHONPATH` = this `src` plus the engine `src` folders (`epc_aea90364`, `epc_drawing` and what it needs). The seeded-error suite against the real pipeline is `harness/tests/unit/test_calc_check_seeded.py`.
