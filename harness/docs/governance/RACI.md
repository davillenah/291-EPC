# RACI base

Source: PRD §5. Detail per organization is an open owner decision (PRD §24, item 2).

| Activity | Engineer of record | Reviewing engineer | `orchestrator` | `electrical_lv` | `calc_check` | `documentation` | `procurement` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Project profile and inputs | A | C | R | C | I | I | I |
| Design criteria (design basis) | A | C | R | R | C | I | I |
| Calculations (through engines) | A | I | C | R | C | I | I |
| Deterministic verification | I | I | C | I | R/A | I | I |
| Drawings and documents | A | C | C | C | C | R | I |
| Lists, BOQ, datasheets, RFQ | A | I | C | C | C | C | R |
| Norm values review | **R/A** | C | I | I | I | I | I |
| Approval and signature | **R/A** | C | I | I | I | I | I |
| Issue and transmittal | A | I | R | I | I | C | I |

R = responsible, A = accountable, C = consulted, I = informed.
