# LL-0004 · Find a system's limit with a size ladder, not with one huge case

- **Discipline:** process
- **Status:** validated
- **Date and origin:** 2026-11-20, stress simulation `pvmax`
- **Resumen (es):** Para hallar el límite, subir el tamaño por escalones y registrar tiempo y memoria de cada uno; un solo caso enorme solo dice que falló.

## Situation
The request was "a PV project at the maximum limit". A single 206 MWp case would only have shown "it dies".

## Solution
Run 4 or 5 sizes (10, 50, 200 MWp) on the same input, record per run: modules, time, peak memory, size of each deliverable and which stage was the heavy one. Sample the memory of the process while it runs (a child process killed by the system leaves no message). Separate "the calculation engine" from "drawings and documents": here the engine took 2 s at 307 440 modules and the drawing stage was the limit. Fix the heavy stage, then rerun the same ladder to prove it.

## Evidence
Before: 10.8 MWp 155 s, 49 MWp 643 s, 206 MWp killed at 14 GB. After: 27 s and 75 s for the last two.

## Sources
None.

## Follow-up
PVX-02: probe beyond 206 MWp and the 2D sheets.
