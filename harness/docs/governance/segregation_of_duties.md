# Segregation of duties

- The agent that produces a result never verifies it.
- `calc_check` runs deterministic checks first and reports with the finding schema.
- Only a person approves norm values or signs.
- Agents cannot write `ssot/`, `deliverables/` or `inputs/` directly; the pipeline does (PRD §21, criterion 8).
- Every number comes from an engine, never from a model (PRD §6, principle 1).
