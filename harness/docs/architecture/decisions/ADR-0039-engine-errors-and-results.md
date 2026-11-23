# ADR-0039: Engine errors and results (bilingual codes, one pattern per engine, no shared runtime package)

Status: proposed (2026-11-23, for the owner to accept). Follows ADR-0038 (engines are called functions). Backlog: COD-21, GEN-08, COD-11, OPT-09.

## Context
Engines fail in different ways today: some raise their own error with a code and an English and Spanish message (`epc_pv.PvError`, `epc_hvac.HvacError`, `epc_receptacles.ReceptaclesError`, `epc_lighting.LightingError`, `epc_plan.PlanError`, `epc_arch.ArchError`), others raise a plain `ValueError` in Spanish only (`epc_calc_common._validate`), and a few answered `None` in silence (COD-11 removed the undocumented ones). There is no list of the errors a user can meet, so the messages cannot be reviewed together and a caller cannot react to a code.

The engines are independent packages, several of them standard-library only (architecture test `test_engine_dependencies`). A shared runtime package for errors would add an edge from every engine to it and change the plugin graph.

## Decisions
1. **Each engine owns one error class** named `<Engine>Error`, a subclass of `ValueError`, built from a **code**: `raise HvacError("err_area", space="S1")`. The instance carries `code`, `en` and `es`; `str(error)` is the English text. This is the pattern `epc_pv` already follows; no shared base class is imported.
2. **Messages live in one module per engine** (`messages.py`): a dict `code -> {"en": ..., "es": ...}` with `{name}` placeholders. English is the source, Spanish its translation (i18n rule). Codes are stable: a message may be reworded, a code is never reused for another meaning.
3. **Results carry warnings the same way:** a list of `{"code", "en", "es"}`. An engine never prints and never returns `None` to mean "failed".
4. **One catalogue, generated (GEN-08):** a build tool reads every `messages.py` and writes `harness/docs/ERROR_CATALOGUE.md` (engine, code, English, Spanish); the gate checks it is fresh, as for the engine contracts (GEN-09).
5. **Input is checked at the entry point (OPT-09)** against the engine's `schema/input.schema.json`, by a small validator inside the engine (standard library only where the engine is), and a failure is an `<Engine>Error` with a code.
6. **Conversion is engine by engine,** with the characterization tests of COD-13 first; texts the user already sees keep their Spanish wording as the `es` template (decision M7).

## Consequences
- A caller (the pipeline, the MCP server) can branch on `error.code` and show the message in the user's language.
- The messages are reviewed in one place; missing translations fail the catalogue check.
- No new dependency between engines; the price is a few lines of the same pattern in each engine.
