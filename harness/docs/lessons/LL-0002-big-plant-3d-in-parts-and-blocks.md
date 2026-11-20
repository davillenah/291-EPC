# LL-0002 · Draw a big plant in parts and blocks, assembled by a master file

- **Discipline:** drawing
- **Status:** validated
- **Date and origin:** 2026-11-20, stress simulation `pvmax`
- **Resumen (es):** Un modelo 3D de planta grande se dibuja con bloques (una mesa, un inversor) insertados, en archivos por sector y un maestro que los une; no una cara por módulo.

## Situation
One face set per module took 206 MB of DXF at 16 128 modules, 939 MB and 10 minutes at 73 680 (7 GB of memory) and ran the run out of memory at 307 440.

## Cause
Every module, post and rail was repeated as geometry. A plant is made of few distinct parts repeated many times.

## Solution
Technical drawing practice: define each distinct part once (a table of n modules at the tilt of its array with its rails and posts; an inverter of one model) and insert it where the layout puts it. Split the plant in sectors of at most 20 000 modules, one file per sector plus a common file (ground, fence, station, inverters), and one master file that attaches them as external references in the same folder. Each file is built, saved and released before the next. A plant up to 20 000 modules stays one file.

## Evidence
49 MWp: 3D from 939 MB to 7.7 MB in 6 files; whole run from 643 s to 27 s. 206 MWp: 27 MB, whole run 75 s, 233 MB of memory. A test compares the faces of the parts with the single model (same geometry). Not checked: opening the master in AutoCAD, Revit or FreeCAD with the parts in place (external references behave differently per program; keep the folder together).

## Sources
None (drawing practice).

## Follow-up
PVX-02 (stage 2D sheets of very big plants), PVX-07 (FreeCAD assembly from the same parts).
