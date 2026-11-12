# `aea90364_reference_cases`

Status: **in development**

The 55 reference cases of the AEA 90364 engine live in one place only: `harness/src/engines/calculation/aea90364/reference_cases/cases` (single source of truth, ADR-0012). The engine tooling (`harness/tools/build/reference_cases.py`) reads them there.

Golden results are regenerated once, officially, after the norm values are verified (decision D27).
