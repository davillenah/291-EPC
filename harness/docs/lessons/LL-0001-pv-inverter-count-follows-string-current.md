# LL-0001 · The inverter count follows the string current, not only the DC/AC ratio

- **Discipline:** PV
- **Status:** validated
- **Date and origin:** 2026-11-20, stress simulation `pvmax` (fictional ground plant, 10.8 MWp and 49 MWp)
- **Resumen (es):** La cantidad de inversores la manda la corriente por entrada MPPT: pedir CC/CA 1,2 dio 90 inversores en el cálculo y 112 instalados (CC/CA real 0,96).

## Situation
With 100 kW string inverters (6 MPPT) and 672 strings, the requested DC/AC ratio of 1.2 gives 90 inverters. The layout installed 112, so the real ratio was 0.96, and the note said 90 at 1.2.

## Cause
Each MPPT input accepts a limited number of strings by current (operating current, and short-circuit current when the data sheet gives it). With the modules of the run, 1 string per input fits, so 672 strings need 672 / 6 = 112 inverters, whatever the ratio asked.

## Solution
Size the inverter count as the larger of (a) the count of the target ratio and (b) the count the strings need at the current limit per input, and state both with the real DC/AC. If the real ratio is far from the target: choose an inverter with more current per input, a module with less current, or combine strings by input only where the data sheet allows. Never accept the target ratio from the note alone: read the real one.

## Evidence
Runs `fix06` and `big09` of the simulation: the note now says 112 installed at 0.96. Not checked: the short-circuit current limit of the Huawei data sheet (the record has no value, flagged as not checked).

## Sources
Manufacturer data sheet of the inverter (record `huawei.sun2000-100ktl-h1`, pending review).

## Follow-up
PVX-01 (done: the note), PV-10 (short-circuit limit per input).
