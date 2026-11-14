# Por qué fallan `engine-aea90364` y `engine-drawing`: informe de diferencias contra los golden

Fecha del informe: 2026-11-14, sobre `feat/pipeline-cierre` (el motor es el mismo que el de `main`). Es un informe, no un cambio: ningún golden, valor de norma ni decisión (D15, D26) fue tocado.

## Causa raíz

Los 87 fallos no son de entorno, rutas, codificación ni dependencias, ni de código nuevo: las pruebas de caracterización comparan el resultado del motor con archivos golden congelados antes de las decisiones del dueño del 2026-11-10 (D6, D13, D16, D17, D18) y el motor ya aplica esas decisiones. Cada diferencia de abajo es el efecto de una decisión ya tomada. Según el BACKLOG, regenerar los golden es el paso `HRN-75` (decisión D27), que va después de que el dueño revise los valores (`NORM-01`). Mientras tanto los fallos no se pueden arreglar sin editar goldens o valores de norma, que solo una persona puede hacer.

## Qué falla y por qué

### engine-aea90364 (84 fallos)

| Prueba | Casos | Qué cambia en el resultado | Decisión que lo explica |
|---|---|---|---|
| `test_every_case_gives_its_golden_result` (`tests/golden/pipeline.json`) | 77 de 78 | `icc_min_a` cambia en 72 valores de 70 casos (p. ej. 7373,1 A contra 7660,0 A); `pe_mm2` en 38 (p. ej. 50 contra 47,5); en 14 casos el aislamiento por defecto es XLPE (método B2, `iz_a` 212 A, `s_termica_mm2` 50) y el golden tiene PVC (método B1, 180 A, 70); `dU`, `du_acum_pct`, `du_propia_pct` en 13 casos (0,825 % contra 0,782 %); `S` y `neutro_mm2` en 8 (300 contra 240 mm²); 3 casos de alumbrado suelto pasan de cumplir a «ninguna sección cumple: usar paralelo» | D13 (corriente de cortocircuito mínima, HRN-51 y HRN-53), D16 y D17 (tensión nominal y límites de caída, HRN-56), D6 y D18 (aislamiento por defecto, HRN-57) |
| mismos casos | 6 | Con método D2 y PVC el motor ahora rechaza el caso con `error: falta la separación entre cables (SEPARACION_CABLES)`; el golden trae un resultado con datos | D18: sin tope ni dato silencioso (HRN-57) |
| `test_ampacity_by_method_insulation_material_phases_grouping_and_temperature` (`tests/golden/core.json`) | 1 | 800 de las combinaciones de la grilla pasan a `error: agrupamiento enterrado de 8 circuitos fuera de la Tabla 771.16.VII.d1` (la tabla solo trae 2 a 6) | D18 |
| `test_the_protection_checks` (`core.json`) | 1 | Los límites de tensión de contacto indirecto son 380 V y 220 V; el golden tiene 400 V y 230 V, y los `cumple` que dependen de ellos cambian (52 valores distintos y 16 claves que el golden no tiene) | D16 (conjunto de tensiones nominales) |
| `test_the_feeder_report_documents` (`core.json`) | 1 | Las memorias de alimentador cambian en 7 textos (`ΔU 13,20 %` contra `12,71 %`; `Icc mín 1731 A` contra `1784 A`) | D13, D16 |
| `test_every_board_gives_its_golden_memo_and_documents` (`tests/golden/memo.json`) | 4 tableros | La memoria y la síntesis de cada tablero heredan los números anteriores | las mismas |

### engine-drawing (3 fallos)

`test_each_board_gives_its_drawings_byte_for_byte_after_normalizing_what_changes_every_run` falla en 3 de sus tableros (`small_sld_mld`, `big_paginated_sld_mld`, `big_tight_criteria_sld`): los DXF y SVG del unifilar y del multifilar y los `*_calculo.json` cambian porque dibujan las secciones, las caídas y las protecciones que calcula `epc_aea90364`. La causa es la misma que arriba; no hay un cambio de dibujo propio.

## Qué debe decidir el dueño

1. Terminar `NORM-01` (revisión de los valores de norma con la hoja `docs/validation/norm_verification_worksheet.xlsx`).
2. Pedir `HRN-75`: regenerar los golden de `aea90364` (`pipeline.json`, `core.json`, `memo.json`) y de `drawing` una sola vez, con un informe de diferencias por decisión. Este informe es el punto de partida; los números de cada decisión salen de comparar el motor actual con los golden actuales.
3. Hasta entonces `engine-aea90364` y `engine-drawing` quedan en rojo; el resto del gate está en verde (43 de 45 en `main`).
