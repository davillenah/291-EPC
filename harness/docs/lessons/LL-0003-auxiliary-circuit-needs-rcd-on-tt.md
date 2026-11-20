# LL-0003 · A plant's auxiliary circuit on a TT board needs its residual-current device from the start

- **Discipline:** electrical LV
- **Status:** validated
- **Date and origin:** 2026-11-20, stress simulation `pvmax` (every run)
- **Resumen (es):** En un tablero TT el circuito auxiliar de la planta debe nacer con diferencial (rcbo); si no, es el único hallazgo major de todas las corridas.

## Situation
Every PV-only run ended with one major finding: the auxiliary service (monitoring, security) had no residual-current protection under a TT earthing scheme.

## Cause
The auxiliary load is a proposal of the harness (a project needs one load) and was created as a plain breaker.

## Solution
Any circuit proposed by the harness for a TT installation is created with its residual-current device (`rcbo`). The engineer of record confirms or changes it.

## Evidence
Run `fix06`: 0 major findings against 1 before. Not checked: the selectivity of the RCBO with the supply protection beyond what stage 7 reports.

## Sources
AEA 90364, protection against indirect contact in TT (clause to be cited by the engineer of record; the norm values stay pending review).

## Follow-up
None.
