# LL-0006 · Describe a part once and regenerate its 3D model from the description

- **Discipline:** drawing
- **Status:** proposed
- **Date and origin:** 2026-11-21, PV stress simulation (fictional project, no client data)
- **Resumen (es):** Cada pieza se describe una sola vez en su registro (medidas, posiciones, detalles) y su modelo 3D se regenera desde ahí, sin volver a investigar la pieza.

## Situation
The first FreeCAD model of the PV plant was a hand-written script: every part (frame, junction box, cells, clamps, posts) was modelled again from memory of the data sheets. The research records already held sizes and positions for most equipment, but only 3 of 6 record families fed a drawing; 35 of the 85 records had elements the generators did not read.

## Cause
The generators were written plant by plant (module, inverter, post) instead of reading the generic description every record carries (`geometry.elements`: box by `size_mm`, or a profile run by `profile_or_accessory_id` and `length_mm`, each with position, rotation and data status).

## Solution
1. The record is the description. Everything needed to redraw the part lives in it, once (ADR-0012): sizes, positions, rotations, profile sections and small details (`features`: the dot at a corner, a label field, a hole, with face, position from the lower-left corner seen from outside, size, depth, status).
2. One generator (`epc_drawing.part_library`) reads any record and writes it as a block in DXF and as a part in a FreeCAD macro; plants instance those parts. A new part needs a record, not new code.
3. Missing data is never filled in: an element without a size or a feature without a position is skipped and listed (`tools/build/part_library.py` prints the list), and every solid takes the layer of its data status so unverified or typical values are visible in the model.
4. Copyright: only extracted values go in the record (JSON), never the data sheet; values stay `pending review`.
Does not apply when a part is decided by a design calculation (a structure section sized by wind): that is an engine result, not a description.

## Evidence
All 85 PV equipment records run through the generator: 50 draw a part; the others list what they lack (post embedment, beams, purlins, braces, connector sets: lengths without positions). The DXF reads back with ezdxf and the macro compiles; the macro was not executed in FreeCAD by the test suite.

## Sources
Equipment records of `epc_pv/data` (each cites its own sources).

## Follow-up
BACKLOG PVX-10 (fill `features` and the missing positions from sourced data; accessory selection rules).
