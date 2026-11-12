# `calculation`

Status: **planned**

load_balance, transformer_sizing, short_circuit, selectivity,

Implemented so far (MIG-37b, split out of `epc_aea90364`): `calc_common` (shared infrastructure, not in the PRD tree), `load_balance`, `voltage_drop`, `feeder_sizing`, `short_circuit`, `grounding`, `selectivity`. `transformer_sizing` is in development (MIG-39a): pure sizing functions with tests; its rating series is pending review and stage 6 inputs are partial. `aea90364` is the orchestrator and the old module names (shims).
