# Change policy

- Corrections by the engineer are written in `reviews/` and become data changes; only the affected stages run again and the next revision carries a difference report (PRD §15).
- Previous signatures of a changed result are marked `superseded`.
- Norm values change only by the owner's decision, recorded in `docs/harness/DECISIONS.md`. Golden results are regenerated once, officially, after the norm values are verified (decision D27).
- Structure and relocation changes follow the migration plan (`docs/harness/MIGRATION_PLAN.md`) and are reversible by file snapshot.
