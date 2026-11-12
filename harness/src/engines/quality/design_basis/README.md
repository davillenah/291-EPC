# epc_design_basis

Status: **in development**

Quality engine (MIG-39f, PRD section 12 stage 2 "Requirements and design basis" and stage 15 "Documents"): builds the DESIGN-BASIS DOCUMENT of a project as structured data and renders it as Spanish plain text. Pure functions, standard library only, no I/O at import, no file output. It copies the profile, criteria, assumptions and requirements, and READS the limits that the calculation engines will apply from those engines' public accessors (imported lazily inside functions, only for reading; the dependency is acyclic: quality reads calculation). Its outputs are drafts (D21).

## Public API
- `build_design_basis_document(profile, *, criteria=None, assumptions=None, requirements=None, norm_status=None, insulation_rules=None)`: dict `{sections, issues, assumptions, open_items, norm_records, status}` with `status` always `draft`. `sections` is a list of `{id, title, items}`, each item `{key, label, value, unit, source, review_status}` (requirement items also carry `status`).
- `design_basis_to_text(doc)`: plain text in Spanish. It is produced only by string templates and the values of the document; no number is typed in a template (checked by a test).

## Sections
1. `identification`: project code, client name, site address / country / installation type, language (copied from the profile).
2. `supply`: source, voltage, earthing system, short-circuit level with unit, origin (copied). A missing origin is an issue.
3. `normative_profile`: jurisdiction and the revision of each part (copied).
4. `design_criteria`: the criteria set and exceptions (profile plus the `criteria` argument, merged like the discipline does) AND the limits read from the engines (below), plus the optional insulation-by-role table.
5. `assumptions`: each with its reason (`source` holds the reason). Text and reason are both required (`ValueError` otherwise); ids `A-01`, `A-02`, ...
6. `requirements`: the requirements copied (`value` = text, `source`, `status`); `open_items` lists the ids with status `open`.
7. `values_note`: what the values mean (draft, pending review = nobody verified the value).

## Limits read from the engines (never typed)
| Item key | Accessor |
| --- | --- |
| `voltage_drop_limit.<iluminacion, tomacorrientes, seccional, motor_regimen, motor_arranque>` | `epc_voltage_drop.aea_voltage_drop.limite_caida_pct(type)` |
| `disconnection_time.sectional.TT`, `.TN`, `.TN_selectivity` | `epc_grounding.aea_earthing.tiempo_seccional_max_s(scheme[, selectividad=True])` |
| `disconnection_time.table.<TT or TN>` (only for the declared scheme) | `epc_grounding.aea_earthing.tiempo_desconexion_max_s(scheme, U0)` |
| `system_voltage_to_earth` (U0) | `epc_load_balance.system_voltage.system_u0(line voltage of the profile)` |
| `c_min` | `epc_short_circuit.short_circuit.C_MIN_BT` |

The module and function of each value are in the item's `source`. A limit that cannot be read (missing accessor or module, a voltage that is not a project system such as 415 V, a voltage missing or not in volts, an earthing system without a table time such as IT) is an entry of `issues`, never a default; the dependent items are then also issues. Insulation by role is NOT read from `epc_aea90364` (that would invert the dependency): the caller may pass `insulation_rules` (`{role: insulation}`), shown with source `caller (insulation_rules)`.

## Input formats
- `profile`: the project profile (PRD section 8). D24 fields `supply.earthing_system` and `supply.short_circuit_level` are mandatory: one `ValueError` lists every missing field. Everything else is optional and a missing value is shown as `null`.
- `criteria`: `{set?, exceptions?}`; `assumptions`: `[{text, reason}]`; `requirements`: the `requirements.schema.json` document (`items` with `id, text, source, status`).
- `norm_status`: optional `{register id: "verified" | "pending review" | "rejected"}`. The engine does NOT read the norm register; the caller passes what it knows. An item's `review_status` is `rejected` if any of its records is, `verified` only if all are, otherwise `pending review` (also for a record not in the mapping).

## Data and provenance
No data table: the engine owns no value, so there is no norm register file. `norm_records` lists the register ids of the values it surfaced (only the ones actually read), mapped by hand in `limits.py` (identifiers, not values): `aea90364.constant.771-19-limites-caida-pct`, `aea90364.constant.771-18-t-seccional-s`, `aea90364.code.aea_earthing.tiempo_seccional_max_s.selectividad`, `aea90364.constant.771-18-iii-tiempos-desconexion-s`, `aea90364.code.system_voltage.u0_380`, `aea90364.code.board_memo.u0_v`, `aea90364.code.aea_pipeline.c_min_bt`. All are `pending` in the register today. The table time is read with U0 as the voltage argument (the accessor calls it `un_v`); this is an assumption for the owner to confirm.

## Not modelled
Verification of the document, approval, sign-off, any value not owned by a calculation engine, requirements negotiation.

## Depends on
The standard library. Lazily, for reading limits only: `epc_voltage_drop`, `epc_grounding`, `epc_load_balance`, `epc_short_circuit`. It never imports a discipline, the platform, the web or `epc_aea90364`.

## Tests
`python -m unittest discover -s tests` or pytest from this folder (every engine `src/` on `PYTHONPATH`, as the gate does).
