# `AR`

Status: **implemented**

Argentina: `jurisdiction.json` (name, locale, currency, frequency, voltages and `packs`, the norm engine each domain uses) and one folder per domain. Moved here from `engine/jurisdictions/AR` (MIG-22).

`electrical/aea90364/` holds the norm data of the AEA 90364 engine (MIG-37a): `aea_tables.json`, `rules/`, `design-criteria.json`, `standard-solutions.json`, `system_voltages.json`. The engine reads it only through `epc_aea90364.norm_data`.
