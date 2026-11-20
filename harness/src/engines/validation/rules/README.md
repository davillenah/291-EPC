# epc-rules

Rules engine (pure Python, standard library only). Loads the promoted `rules.json` of the norm engines a jurisdiction names (`harness/config/normative/<CC>/jurisdiction.json`, `packs`), queries them and checks project data: PASS, FAIL or not evaluated (a missing datum is reported, never guessed). Production sees only verified standards.

```
from epc_rules import RuleSet
rs = RuleSet.load("AR", "electrical", env="production")
rs.check({"reserva_pct": 15}, installation_type="dwellings", topic="bandejas")
```

CLI (from `harness/src/engines/validation/rules/src`): `python -m epc_rules list|query|check`.
Tests: `python -m unittest discover -s tests` with `PYTHONPATH=src`.
Rule format: `harness/schemas/rules.schema.json`. Ingestion pipeline: `harness/src/engines/validation/standards`.

## Status in the pipeline
Development and review tool: no stage of `electrical_lv` imports it yet, and the norm engines have no promoted `standards/<ID>/rules.json` (audit 2026-11-20, AUD-01 in `docs/BACKLOG.md`). It is not part of a project run until that task is done.
