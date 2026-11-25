# Registro de normas

Generado por `python harness/tools/build/norm_register.py --report`; no se edita a mano. Lista cada valor de norma con su cláusula, página y fuente, para que el dueño lo verifique contra la norma oficial. Solo el dueño cambia el estado (`pending` -> `verified`/`rejected`). Los datos viven en un solo lugar: los registros con ubicación JSON solo apuntan al archivo.

## Resumen

- Registros a mano: **302** en 33 archivos.
- Reglas indexadas automáticamente: **200**.
- Sin cláusula: **202**.
- Conflictos o duplicados señalados: **21**.

### Registros a mano por motor, procedencia y estado

| Motor | Procedencia | Estado | Registros |
|---|---|---|---:|
| src | convention | pending | 23 |
| src | design-default | pending | 57 |
| src | illustrative | pending | 3 |
| src | norm | pending | 133 |
| src | physics | pending | 14 |
| src | teaching | pending | 6 |
| src | typical | pending | 66 |

### Reglas indexadas por motor

| Motor | Reglas | Con revisión aprobada |
|---|---:|---:|
| aea90364 | 177 | 0 |
| lighting | 23 | 0 |

## aea90364 / code-commercial-series

Archivo: `harness/src/engines/calculation/aea90364/src/epc_aea90364/norm_register/code-commercial-series.json` (5 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `aea90364.code.aea_pipeline.serie_in_a` | - | - | - | `[6, 10, 13, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160...` | A | convention | medium | pending | includes 13 A and 6 A; no standard series cited (IEC 60898-1 / 60947-2 preferred values); no clause in code |
| `aea90364.code.aea_pipeline.serie_icu_ka` | - | - | - | `[6, 10, 15, 20, 25, 36, 50, 70, 100]` | kA | convention | medium | pending | no clause in code |
| `aea90364.code.aea_pipeline.serie_s_mm2` | AEA 90364-7-771 (2006) | 771.16.I | - | `[1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 18...` | mm2 | norm | medium | pending | expression tuple(sorted(CO.IZ_771_16_I)); value transcribed; conflicts with aea90364.code.aea_export.serie_s_mm2: the export series is wider (0.5 to 630 mm2) |
| `aea90364.code.aea_export.serie_s_mm2` | - | - | - | `[0.5, 0.75, 1, 1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95...` | mm2 | convention | medium | pending | conflicts with aea90364.code.aea_pipeline.serie_s_mm2: this series has 0.5, 0.75, 400, 500, 630 mm2 not in the pipeline; no clause in code |
| `aea90364.code.aea_pipeline.in_max_mcb_a` | IEC 60898-1 | - | - | `63` | A | norm | low | pending | same 63 A boundary as aea90364.code.board_memo.curve_band.t_convencional; no clause in code |

## aea90364 / code-conductors-ampacity

Archivo: `harness/src/engines/calculation/aea90364/src/epc_aea90364/norm_register/code-conductors-ampacity.json` (15 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `aea90364.code.aea_conductors.alfa_cu` | - | - | - | `aea_tables.json#/constantes/conductor_alfa_cu` | 1/C | physics | high | pending | no clause in code |
| `aea90364.code.aea_conductors.factors_harmonics` | AEA 90364-7-771 (2006) | 771.16.XIII | - | `aea_tables.json#/constantes/771.16.XIII_factores_armonicos` | - | norm | medium | pending | not in aea_tables.json (the JSON meta lists XII as unreadable; XIII is simply absent): value lives only in code; last row upper limit is math.inf in code, written as null in value |
| `aea90364.code.aea_conductors.pe_section.pasos` | AEA 90364-7-771 (2006) | 771.18.3 | - | `aea_tables.json#/constantes/771.18.3_pe_pasos` | mm2 | norm | medium | pending | one implementation (ENG-14): aea_earthing.seccion_pe_mm2 calls aea_conductors.pe_section; clause cited as 771.18.3 here and as 771-C.II in the earthing docstring; the S/2 result is rounded up to the next commercial section of Table 771.16.I (47.5 -> 50 mm2), cases s1 and s2; the series is read from the 771.16.I data; board_figures.py note also hardcodes 'S/2 si S>35 mm2' as text |
| `aea90364.code.aea_conductors.neutral_section.umbral` | - | - | - | `aea_tables.json#/constantes/neutro_seccion_igual_hasta_mm2` | mm2 | norm | low | pending | no clause cited; the 16 mm2 threshold is the copper one: aluminium is usually 25 mm2 in IEC 60364-5-52 (check, not changed); no clause in code |
| `aea90364.code.aea_ampacity.seccion_min_al_mm2` | AEA 90364-7-771 (2006) | 771.13 | - | `aea_tables.json#/constantes/771.13_seccion_minima_al_mm2` | mm2 | norm | medium | pending | module docstring: 'Aluminio solo desde 16 mm2 (AEA 771.13)' [VERIFICAR]; related JSON value is the PEN minimum Al 16 (/constantes/771.13_pen_minima_mm2/al), not a general Al minimum |
| `aea90364.code.aea_ampacity.alfa` | - | - | - | `aea_tables.json#/constantes/conductor_alfa_al` | 1/C | physics | medium | pending | cu entry is aea_conductors.ALFA_CU (not a literal here); the Al value 0.00403 is only here; no clause in code |
| `aea90364.code.aea_ampacity.r20_al_ohm_km` | IEC 60228 | - | - | `aea_tables.json#/constantes/conductor_r20_al_ohm_km` | ohm/km | norm | medium | pending | differs from Cu x JSON factor_aluminio (1.64): the table ratios Al/Cu are 1.65 to 1.68 (e.g. 10 mm2: 3.08 vs 1.83x1.64=3.00); used by aea_ampacity; aea_earthing._r_km uses Cu x 1.64 instead: two Al resistances in the engine; no clause in code |
| `aea90364.code.aea_ampacity.fuentes` | AEA 90364-7-771 (2006) | 771.16 | - | `aea_tables.json#/constantes/771.16_metodos_tabla_fuente` | - | norm | low | pending | rule encoded in lambdas: value is a transcription, not a literal; any method not listed falls back to D2 (771.16.VI) |
| `aea90364.code.aea_ampacity.agrupamiento` | AEA 90364-7-771 (2006) | 771.16 | - | `aea_tables.json#/constantes/771.16_metodos_agrupamiento` | - | norm | low | pending | rule encoded in lambdas: value is a transcription; the item numbers refer to table 771.16.IV items; clause cited only as 771.16 |
| `aea90364.code.aea_ampacity.factores.clase5` | AEA 90364-7-771 (2006) | - | - | `aea_tables.json#/constantes/771.16_factor_clase5` | - | norm | low | pending | docstring of aea_tables states 0.95 for class 5, no clause; no clause in code |
| `aea90364.code.aea_route.kinds` | AEA 90364-7-771 (2006) | 771.16 | - | `aea_tables.json#/constantes/ruta_tipos_tramo_metodos` | - | norm | low | pending | mapping chosen in code; module header cites 771.16.I a VII and IEC 60364-5-52 |
| `aea90364.code.aea_route.limites_validacion` | - | - | - | `{"length_m": [0, 5000], "circuits": [1, 20], "ambient_c":...` | - | design-default | low | pending | engineering bounds, not norm values; rho 0.3-5 K*m/W should cover the soil-resistivity table; no clause in code |
| `aea90364.code.cable_thermal.t_adiabatico_max_s` | IEC 60364-4-43 | - | - | `aea_tables.json#/constantes/cable_t_adiabatico_max_s` | s | norm | low | pending | marked [VERIFICAR] in code; no clause in code |
| `aea90364.code.cable_thermal.t_corto_s` | IEC 60364-4-43 | - | - | `aea_tables.json#/constantes/cable_t_corto_s` | s | norm | low | pending | marked [VERIFICAR] in code; no clause in code |
| `aea90364.code.aea_conductors.k_adiabatico_771.alias` | AEA 90364-7-771 (2006) | 771.19.II | - | `aea_tables.json#/constantes/771.19.II_k_aislaciones` | - | norm | medium | pending | - |

## aea90364 / code-defaults

Archivo: `harness/src/engines/calculation/aea90364/src/epc_aea90364/norm_register/code-defaults.json` (20 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `aea90364.code.aea_pipeline.default.tension_v` | - | - | - | `380.0` | V | design-default | low | pending | same value as JSON criterion aea90364.criterion.nominal-voltage-v (380); duplicated in grouping.py, board_figures.py, aea_feeder_report.py and backend models.py; no clause in code |
| `aea90364.code.aea_pipeline.default.icc_ka` | - | - | - | `10.0` | kA | design-default | low | pending | duplicated in grouping.py, aea_feeder_report.py, board_memo (10) and backend models.py; no clause in code |
| `aea90364.code.aea_pipeline.default.fp` | - | - | - | `0.85` | - | design-default | low | pending | duplicated in grouping.py, board_figures.py and backend models.py; no clause in code |
| `aea90364.code.aea_pipeline.default.insulation` | - | - | - | `"PVC"` | - | design-default | low | pending | conflicts with aea90364.criterion.insulation: design-criteria.json default is XLPE, code fallback is PVC; no clause in code |
| `aea90364.code.aea_pipeline.default.material` | - | - | - | `"cobre"` | - | design-default | low | pending | same as aea90364.criterion.conductor-material default (cobre); no clause in code |
| `aea90364.code.aea_pipeline.default.rcd_ma` | - | - | - | `30.0` | mA | norm | low | pending | same value as aea90364.criterion.rcd-sensitivity-ma (30); no clause in code |
| `aea90364.code.aea_pipeline.default.ambient_c` | - | - | - | `40.0` | C | norm | low | pending | same value as aea90364.criterion.ambient-temp-c (40); 40 C is the reference of table 771.16.I; no clause in code |
| `aea90364.code.aea_pipeline.default.soil_c` | - | - | - | `25.0` | C | norm | low | pending | same value as aea90364.criterion.soil-temp-c (25); no clause in code |
| `aea90364.code.aea_pipeline.default.rho_kmw` | - | - | - | `1.0` | K*m/W | norm | low | pending | same value as aea90364.criterion.soil-resistivity-kmw (1); no clause in code |
| `aea90364.code.aea_ampacity.default.ambiente_suelo_rho` | - | - | - | `{"ambient_c": 40.0, "soil_c": 25.0, "rho_kmw": 1.0}` | - | design-default | low | pending | duplicated literals of the pipeline defaults; no clause in code |
| `aea90364.code.aea_pipeline.default.rendimiento` | - | - | - | `1.0` | - | design-default | low | pending | no clause in code |
| `aea90364.code.aea_pipeline.default.temp_c` | - | - | - | `70.0` | C | design-default | low | pending | CLI also defaults to 70 C; XLPE uses 90 C via aea_ampacity.temp_conductor; no clause in code |
| `aea90364.code.aea_pipeline.hp_w` | - | - | - | `745.7` | W | physics | high | pending | no clause in code |
| `aea90364.code.aea_pipeline.hp_cv_w` | - | - | - | `735.49875` | W | physics | high | pending | no clause in code |
| `aea90364.code.grouping.default.max_circuits` | - | - | - | `6` | circuits | design-default | low | pending | no clause in code |
| `aea90364.code.grouping.default.max_ib_a` | - | - | - | `40` | A | design-default | low | pending | also default 40 in solutions.py validation; no clause in code |
| `aea90364.code.grouping.default.tablero` | - | - | - | `{"voltage_v": 380.0, "fp": 0.85, "icc_ka": 10.0}` | - | design-default | low | pending | duplicated literals of the pipeline defaults; no clause in code |
| `aea90364.code.board_figures.default.tablero` | - | - | - | `{"voltage_v": 380.0, "fp": 0.85, "frequency_hz": 50}` | - | design-default | low | pending | duplicated literals of the pipeline defaults; no clause in code |
| `aea90364.code.aea_feeder_report.default.tablero` | - | - | - | `{"voltage_v": 380.0, "icc_ka": 10.0}` | - | design-default | low | pending | duplicated literals; the report text also hardcodes reactance 0,08 ohm/km; no clause in code |
| `aea90364.code.conductor_selection.cli.fp` | - | - | - | `0.9` | - | design-default | low | pending | differs from the 0.85 default of the pipeline; no clause in code |

## aea90364 / code-demand-loads

Archivo: `harness/src/engines/calculation/aea90364/src/epc_aea90364/norm_register/code-demand-loads.json` (13 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `aea90364.code.aea_demand.u_mono_v` | - | - | - | `aea_tables.json#/constantes/tension_nominal_defecto_v/valor/mono` | V | convention | medium | pending | docstring HIPOTESIS: 220/380 V (AEA 771/770); no clause; other modules default to 220 V too (aea_voltage_drop) and 230 V U0 (board_memo, aea_protection); no clause in code |
| `aea90364.code.aea_demand.u_tri_v` | - | - | - | `aea_tables.json#/constantes/tension_nominal_defecto_v/valor/tri` | V | convention | medium | pending | docstring HIPOTESIS: 220/380 V (AEA 771/770); no clause; aea_protection default line voltage is 400 V; no clause in code |
| `aea90364.code.aea_demand.va_boca_vivienda` | AEA 90364-7-771 (2006) | 771.9.1 | - | `aea_tables.json#/constantes/771.9.1_va_boca_vivienda` | VA | norm | medium | pending | - |
| `aea90364.code.aea_demand.va_boca_770` | AEA 90364-7-770 (2017) | 770.8.I | - | `aea_tables.json#/constantes/770.8.I_va_boca` | VA | norm | medium | pending | - |
| `aea90364.code.aea_demand.va_tug` | AEA 90364-7-771 (2006) | 771.9 | - | `aea_tables.json#/constantes/771.9_va_tug` | VA | norm | medium | pending | docstring of the module: §9; the table number (771.9.I per the JSON title) is not cited in code |
| `aea90364.code.aea_demand.va_tue` | AEA 90364-7-771 (2006) | 771.9 | - | `aea_tables.json#/constantes/771.9_va_tue` | VA | norm | medium | pending | docstring of the module: §9; the table number is not cited in code |
| `aea90364.code.aea_demand.desequilibrio_max_pct` | AEA 90364-7-770 (2017) | 770.8.3.4 | - | `aea_tables.json#/constantes/770.8.3.4_desequilibrio_max_pct` | % | norm | medium | pending | - |
| `aea90364.code.aea_demand.grados_771` | AEA 90364-7-771 (2006) | 771.8.I, 771.8.IV, 771.8.IX | - | `aea_tables.json#/constantes/771.8_grados_electrificacion` | m2; kVA | norm | medium | pending | last row limit is math.inf in code, written as null; the file mixes tables 771.8.I (dwellings), 771.8.IV (offices and shops) and 771.8.IX (other premises): which table feeds 'local' is not stated |
| `aea90364.code.aea_demand.conjuntos_771_iii` | AEA 90364-7-771 (2006) | 771.9.III | - | `aea_tables.json#/constantes/771.9.III_conjuntos_coeficientes` | - | norm | medium | pending | threshold 15.5 units is not an integer: check against the table |
| `aea90364.code.aea_demand.grade_electrification_770.umbrales` | AEA 90364-7-770 (2017) | 770.7.I | - | `aea_tables.json#/constantes/770.7.I_grados_electrificacion` | m2 | norm | medium | pending | same 60/130/200 limits as the dwelling grades of _GRADOS_771 (771.8.I) |
| `aea90364.code.aea_demand.requiere_trifasico` | - | - | - | `aea_tables.json#/constantes/demanda_trifasico_recomendado` | VA; A | typical | low | pending | no clause in code |
| `aea90364.code.aea_demand.corriente_alimentador_motores.factor` | - | - | - | `aea_tables.json#/constantes/motor_alimentador_factor_mayor` | - | norm | low | pending | same 1.25 as aea90364.code.aea_pipeline.margin_motor (used for In of one motor); no clause in code |
| `aea90364.code.aea_demand.factor_parallel` | IEC 60364-5-52 | - | - | `aea_tables.json#/constantes/conductores_paralelo_factores` | - | norm | low | pending | module NORMA line cites IEC 60364-5-52 (paralelo) with [VERIFICAR]; no clause in code; no clause in code |

## aea90364 / code-motor-backup-reactive-lightning

Archivo: `harness/src/engines/calculation/aea90364/src/epc_aea90364/norm_register/code-motor-backup-reactive-lightning.json` (3 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `aea90364.code.aea_pipeline.margin_motor` | - | - | - | `1.25` | - | typical | low | pending | duplicated literal; same 1.25 as aea90364.code.aea_demand.corriente_alimentador_motores.factor; no clause in code |
| `aea90364.code.aea_backup.arranque_defecto` | - | - | - | `1.0` | x In | design-default | low | pending | no clause in code |
| `aea90364.code.aea_lightning.superficie_captacion.radio_3h` | IEC 62305-2 | - | - | `aea_tables.json#/constantes/descargas_radio_captacion_factor_altura` | x H | norm | low | pending | header: rules not reviewed, values typical; no clause in code; no clause in code |

## aea90364 / code-non-aea

Archivo: `harness/src/engines/calculation/aea90364/src/epc_aea90364/norm_register/code-non-aea.json` (7 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `aea90364.code.hazen_williams.constante_hw` | NFPA 13 | - | - | `605000.0` | - | norm | medium | pending | docstring: NFPA 13 use is [VERIFICAR], form and constant from memory, no clauses; no clause in code |
| `aea90364.code.hazen_williams.exp_q` | NFPA 13 | - | - | `1.85` | - | norm | medium | pending | docstring: NFPA 13 use is [VERIFICAR], form and constant from memory, no clauses; no clause in code |
| `aea90364.code.hazen_williams.exp_d` | NFPA 13 | - | - | `4.87` | - | norm | medium | pending | docstring: NFPA 13 use is [VERIFICAR], form and constant from memory, no clauses; no clause in code |
| `aea90364.code.hazen_williams.rho_agua` | - | - | - | `1000.0` | kg/m3 | physics | medium | pending | no clause in code |
| `aea90364.code.hazen_williams.g` | - | - | - | `9.80665` | m/s2 | physics | medium | pending | no clause in code |
| `aea90364.code.hvac_airflow.rho_aire` | ASHRAE Fundamentals | - | - | `1.2` | kg/m3 | physics | medium | pending | DIFFERENT from the air constant of engine/hvac config AIR_SENSIBLE_W_PER_LS_K (1.23 W per L/s per K): rho*cp here = 1.2*1.006 = 1.207 kW/(m3/s*K), 1.9 % lower than 1.23; no clause in code |
| `aea90364.code.hvac_airflow.cp_aire` | ASHRAE Fundamentals | - | - | `1.006` | kJ/(kg*K) | physics | medium | pending | DIFFERENT from the air constant of engine/hvac config AIR_SENSIBLE_W_PER_LS_K (1.23): see aea90364.code.hvac_airflow.rho_aire; no clause in code |

## aea90364 / code-panel-thermal

Archivo: `harness/src/engines/calculation/aea90364/src/epc_aea90364/norm_register/code-panel-thermal.json` (5 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `aea90364.code.aea_panel_thermal.k_e` | AEA 90364-7-770 (2017) | 770-B | - | `aea_tables.json#/constantes/770-B_k_e` | - | norm | medium | pending | annex B only (module header); the table number is not cited in code |
| `aea90364.code.aea_panel_thermal.k_cableado` | AEA 90364-7-770 (2017) | 770-B | - | `aea_tables.json#/constantes/770-B_k_cableado` | - | norm | medium | pending | annex B only (module header); table number not cited |
| `aea90364.code.aea_panel_thermal.k_circuitos` | AEA 90364-7-770 (2017) | 770-B.XII | - | `aea_tables.json#/constantes/770-B.XII_k_circuitos` | - | norm | medium | pending | docstring lists the bands as 2-3, 4-5, 6-9, >=10 |
| `aea90364.code.aea_panel_thermal.pd_polo` | AEA 90364-7-770 (2017) | 770-B.XI | - | `aea_tables.json#/constantes/770-B.XI_pd_polo_w` | W/pole | norm | medium | pending | - |
| `aea90364.code.aea_panel_thermal.pdc_dif` | AEA 90364-7-770 (2017) | 770-B.X | - | `aea_tables.json#/constantes/770-B.X_pdc_diferencial_a` | A (breaking capacity) | norm | medium | pending | unit of the second value is not stated in code (500 to 1000, presumably A) |

## aea90364 / code-protection-earthing

Archivo: `harness/src/engines/calculation/aea90364/src/epc_aea90364/norm_register/code-protection-earthing.json` (19 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `aea90364.code.aea_earthing.ra_maxima.factor_adopcion` | AEA 90364-7-771 (2006) | 771.3.I | - | `aea_tables.json#/constantes/771.18_ra_factor_adopcion` | - | norm | low | pending | the code does not explain why 0.5 (half of UL/IDn); check it is in the table or is a project margin; adopted in aea_earthing.ra_maxima (decision D11); aea_protection and board_memo call it (one function) |
| `aea90364.code.aea_earthing.resistance_rod.simplificada` | AEA 90364-7-771 (2006) | 771-C.10 | - | `{"ld_min": 25, "ld_max": 3000, "k_ld_to_100": 0.75, "k_ld...` | - | norm | medium | pending | - |
| `aea90364.code.aea_earthing.resistance_rod.exacta` | AEA 90364-7-771 (2006) | 771-C.10 | - | `{"ln_argument_factor": 8, "subtracted": 1}` | - | norm | medium | pending | - |
| `aea90364.code.aea_earthing.resistance_conductor_horizontal.simplificada` | AEA 90364-7-771 (2006) | 771-C.10 | - | `2.0` | - | norm | medium | pending | - |
| `aea90364.code.aea_earthing.resistance_conductor_horizontal.exacta` | AEA 90364-7-771 (2006) | 771-C.10 | - | `{"ln_4L_d": 1, "ln_L_h": 1, "constant": -2, "term_2h_L": ...` | - | norm | medium | pending | docstring says the series is truncated at the terms cited |
| `aea90364.code.aea_earthing.resistencia_placa_circular.coeficientes` | AEA 90364-7-771 (2006) | 771-C.10 | - | `{"first": 0.5, "D_over_4_pi_h": 1, "cubic": "7/384", "qui...` | - | norm | medium | pending | docstring says the series is truncated at the terms cited |
| `aea90364.code.aea_earthing.resistencia_malla.sverak` | IEEE Std 80 | - | - | `{"area_factor": 20.0, "default_depth_m": 0.6}` | - | norm | low | pending | marked [VERIFICAR] in the code; not an AEA norm; no clause in code |
| `aea90364.code.aea_protection.verifica_tn_u0_v_default` | AEA 90364-4-41 | 41.3 | - | `230.0` | V | convention | medium | pending | same value as aea90364.code.board_memo.u0_v (230 V); the removed web backend derived U0 = voltage/sqrt(3) (219 V at 380 V); see decision D16 |
| `aea90364.code.aea_protection.verifica_it_segunda_falla.u_v_default` | AEA 90364-4-41 | 41.3 | - | `400.0` | V | convention | medium | pending | other modules default to 380 V line voltage (TENSION_V, nominal_voltage_v) |
| `aea90364.code.system_voltage.u0_380` | - | - | - | `system_voltages.json#/systems/1/u0_v` | V | convention | medium | pending | owner decision D16 (2026-11-10): 230/400 V -> U0 = 230 V; 220/380 V -> U0 = 220 V; no clause cited; added by MIG-36f; pending review |
| `aea90364.code.board_memo.k_mag` | IEC 60898-1 / IEC 60947-2 | - | - | `aea_tables.json#/constantes/curva_disparo_magnetico_k` | x In | norm | medium | pending | MCCB (5, 10) is a project assumption of adjustable magnetic trip, not a standard range; same B/C/D upper limits as aea_pipeline.K_MAGNETICO_C for C (10); no clause in code |
| `aea90364.code.board_memo.u0_v` | - | - | - | `system_voltages.json#/systems/0/u0_v` | V | convention | medium | pending | the removed web backend used voltage_v/sqrt(3) (219 V at 380 V) while board_memo uses fixed 230 V (decision D16); no clause in code; decision D16: unify with the project's system (230/400 -> 230 V, 220/380 -> 220 V); left as is in ENG-14; MIG-36f: the constant U0_V of board_memo no longer exists; U0 comes from system_voltage.system_u0 and this record points to the 400 V system row of data/system_voltages.json (value unchanged, still pending review) |
| `aea90364.code.board_memo.ratio_termico` | - | - | - | `aea_tables.json#/constantes/termico_ratio_min` | - | typical | low | pending | rule of thumb; no standard cited in code; no clause in code |
| `aea90364.code.board_memo.curve_band.t_convencional` | IEC 60898-1 / IEC 60947-2 | - | - | `aea_tables.json#/constantes/curva_banda_tiempos/valor/t_convencional` | s | norm | medium | pending | same 63 A boundary used for MCB: aea_pipeline.IN_MAX_MCB_A; no clause in code |
| `aea90364.code.board_memo.curve_band.punto_2_55` | IEC 60898-1 | - | - | `aea_tables.json#/constantes/curva_banda_tiempos/valor/punto_2_55` | s | norm | medium | pending | no clause in code |
| `aea90364.code.board_memo.curve_band.tiempos_magneticos` | IEC 60898-1 / IEC 60947-2 | - | - | `aea_tables.json#/constantes/curva_banda_tiempos/valor/tiempos_magneticos` | s | convention | low | pending | plot construction values, not a normative time; no clause in code |
| `aea90364.code.board_memo.curve_letter` | - | - | - | `{"motors_mcb_rcbo": "D", "other": "C", "mccb": "MCCB"}` | - | design-default | medium | pending | project assumption stated in the memo ('supuestos'); no clause in code |
| `aea90364.code.board_memo.selectividad.curva_aguas_arriba_defecto` | - | - | - | `{"in_limit_a": 63, "above": "MCCB", "below": "C"}` | A | design-default | low | pending | no clause in code |
| `aea90364.code.aea_earthing.tiempo_seccional_max_s.selectividad` | AEA 90364-7-771 (2006) | 771.18 | - | `aea_tables.json#/constantes/771.18_t_seccional_selectividad_tn_s` | s | norm | medium | pending | owner decision D25: TN sectional 2 s by default; up to 5 s only when selectivity justifies it |

## aea90364 / code-short-circuit

Archivo: `harness/src/engines/calculation/aea90364/src/epc_aea90364/norm_register/code-short-circuit.json` (13 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `aea90364.code.short_circuit.c_max_bt_tol_10` | IEC 60909-0 | - | - | `aea_tables.json#/constantes/icc_c_max_tol_10` | - | norm | medium | pending | marked [VERIFICAR] in code; no clause in code; also read by aea_icc_factors.C_MAX_RED (same constant icc_c_max_tol_10) |
| `aea90364.code.short_circuit.temp_min_c` | IEC 60909-0 | - | - | `aea_tables.json#/constantes/icc_temp_min_c` | C | norm | low | pending | marked [VERIFICAR] in code; fixed 70 C even for XLPE (90 C service temperature in aea_ampacity.TEMP_CONDUCTOR_C); JSON uses a factor 1.2 at service temperature; no clause in code |
| `aea90364.code.short_circuit.xr_red_defecto` | IEC 60909-0 | - | - | `aea_tables.json#/constantes/icc_xr_red_defecto` | - | typical | low | pending | marked [VERIFICAR] in code; no clause in code |
| `aea90364.code.short_circuit.umbral_motores_despreciable` | IEC 60909-0 | - | - | `aea_tables.json#/constantes/icc_motores_despreciable_pct` | fraction | norm | medium | pending | marked [VERIFICAR] in code; no clause in code; also read by aea_icc_factors.LIM_MOTORES_I_PCT (same constant icc_motores_despreciable_pct, 5 %, eq. [108]) |
| `aea90364.code.short_circuit.factor_kt.coeficientes` | AEA IT 90909-1 (2005) | eq. [65] | - | `aea_tables.json#/constantes/icc_factor_kt` | - | norm | medium | pending | marked [VERIFICAR] in code; equation number [65] comes from the aea_icc_factors docstring |
| `aea90364.code.short_circuit.factor_kappa.coeficientes` | AEA IT 90909-1 (2005) | eq. [68] | - | `aea_tables.json#/constantes/icc_factor_kappa` | - | norm | medium | pending | marked [VERIFICAR] in code; equation [68] is cited in the aea_icc_factors/aea_icc_decay docstrings |
| `aea90364.code.short_circuit.factor_kappa.x_cero` | AEA IT 90909-1 (2005) | eq. [68] | - | `aea_tables.json#/constantes/icc_factor_kappa/valor/base` | - | convention | low | pending | limit case chosen in code; not stated in the standard excerpt cited |
| `aea90364.code.aea_icc_factors.rigido_max_u_ratio` | AEA IT 90909-1 (2005) | - | - | `aea_tables.json#/constantes/icc_rigido_max_u_ratio` | - | norm | medium | pending | stated only in the FORMULAS part of the docstring, no equation number; no clause in code |
| `aea90364.code.aea_icc_factors.lim_motores_suma_irm_pct` | AEA IT 90909-1 (2005) | eq. [110] | - | `aea_tables.json#/constantes/icc_motores_suma_irm_pct` | % | norm | medium | pending | - |
| `aea90364.code.aea_icc_decay.u_fmax` | AEA IT 90909-1 (2005) | - | - | `aea_tables.json#/constantes/icc_u_fmax` | - | norm | low | pending | not used anywhere in the engine code (only defined); meaning is not documented in the module; keys are tuples (rotor, case) rendered as Python tuple text in value (validator form); no clause in code |
| `aea90364.code.aea_icc_decay.n_factor.t2_sobre_t1` | AEA IT 90909-1 (2005) | eq. [102b] | - | `{"t2_over_t1": 0.1}` | - | norm | medium | pending | coefficients 20, 10, 11, 5 and 5.5 in the expression derive from 0.1 (T''dN = 0.1*T'dN) |
| `aea90364.code.aea_pipeline.c_max_bt` | AEA 90909-0 | - | - | `1.05` | - | norm | medium | pending | duplicated literal; same value as aea90364.code.short_circuit.c_max_bt_tol_6 (1.05) and JSON /constantes/impedancias_estandar/c_fuente_max (1.05); no clause in code |
| `aea90364.code.aea_pipeline.c_min_bt` | AEA 90909-0 | - | - | `0.95` | - | norm | medium | pending | alias of short_circuit.C_MIN_BT (JSON /constantes/impedancias_estandar/c_tension_min, 0.95); no own literal since D13; no clause in code |

## aea90364 / code-special-locations

Archivo: `harness/src/engines/calculation/aea90364/src/epc_aea90364/norm_register/code-special-locations.json` (8 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `aea90364.code.aea_special_locations.mu0` | - | - | - | `1.2566370614359173e-06` | H/m | physics | high | pending | written as 4.0e-7*math.pi, an expression; no clause in code |
| `aea90364.code.aea_special_locations.b_lim_t` | AEA 90364-7-701 (2012) | - | - | `aea_tables.json#/constantes/701_b_lim_t` | T | norm | medium | pending | no clause in code |
| `aea90364.code.aea_special_locations.radio_zona2_m` | AEA 90364-7-701 (2012) | - | - | `aea_tables.json#/constantes/701_radio_zona2_m` | m | norm | medium | pending | no clause in code |
| `aea90364.code.aea_special_locations.max_outlets_load_multiple` | AEA 90364-7-722 (2018) | - | - | `aea_tables.json#/constantes/722_carga_multiple/valor/max_tomas` | count | norm | medium | pending | no clause in code |
| `aea90364.code.aea_special_locations.i_min_load_multiple_to` | AEA 90364-7-722 (2018) | - | - | `aea_tables.json#/constantes/722_carga_multiple/valor/i_min_a` | A | norm | medium | pending | no clause in code |
| `aea90364.code.aea_special_locations.load_multiple_complies.mitad` | AEA 90364-7-722 (2018) | - | - | `aea_tables.json#/constantes/722_carga_multiple/valor/fraccion_bocas` | - | norm | medium | pending | no clause in code |
| `aea90364.code.aea_special_locations.idn_diferencial_ev_ma` | AEA 90364-7-722 (2018) | - | - | `aea_tables.json#/constantes/ev_idn_diferencial_ma` | mA | norm | medium | pending | no clause in code |
| `aea90364.code.aea_special_locations.i_cc_deteccion_ma` | AEA 90364-7-722 (2018) | - | - | `aea_tables.json#/constantes/ev_i_cc_deteccion_ma` | mA | norm | medium | pending | no clause in code |

## aea90364 / code-voltage-drop

Archivo: `harness/src/engines/calculation/aea90364/src/epc_aea90364/norm_register/code-voltage-drop.json` (6 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `aea90364.code.aea_voltage_drop.fraccion_ilum_771` | AEA 90364-7-771 (2006) | 771.9.1 | - | `aea_tables.json#/constantes/771.9.1_fraccion_iluminacion` | - | norm | medium | pending | clause 771.9.1 is cited for the same 66 % in aea_demand, not in this module |
| `aea90364.code.aea_voltage_drop.fraccion_ilum_770` | AEA 90364-7-770 (2017) | 770.8.I | - | `aea_tables.json#/constantes/770.8.I_fraccion_iluminacion` | - | norm | medium | pending | clause 770.8.I is cited for 2/3 in aea_demand; value is the expression 2.0 / 3.0 in code |
| `aea90364.code.aea_voltage_drop.tension_defecto` | - | - | - | `aea_tables.json#/constantes/tension_nominal_defecto_v` | V | convention | medium | pending | hardcoded three times in this module (lines of caida_gdc, longitud_maxima, seccion_minima); same values as aea_demand.U_MONO_V / U_TRI_V and the 380 V defaults of the pipeline; no clause in code |
| `aea90364.code.aea_voltage_drop.gdc_arranque.rango_secciones` | AEA 90364-7-771 (2006) | 771.19 | - | `aea_tables.json#/constantes/771.19_gdc_arranque_secciones_mm2` | mm2 | norm | medium | pending | docstring: 'GDC de arranque definido para 1,5-25 mm2 y 35-70 mm2'; same 70 mm2 cut in aea_motor.caida_arranque (reads the same JSON constant) |
| `aea90364.code.aea_pipeline.du_acum_max_pct` | - | - | - | `5.0` | % | norm | low | pending | no clause in the code; related to 3 % + 1 % + ... limits of AEA 771.19 (total 5 %); same 5 % as JSON aea90364.constant.771-19-limites-caida-pct motor_regimen (coincidence of values, different meaning) and as aea_export.DU_AVISO_PCT; no clause in code |
| `aea90364.code.aea_export.du_aviso_pct` | - | - | - | `5.0` | % | design-default | low | pending | duplicated literal; same 5 % as aea90364.code.aea_pipeline.du_acum_max_pct; no clause in code |

## aea90364 / constants

Archivo: `harness/src/engines/calculation/aea90364/src/epc_aea90364/norm_register/constants.json` (23 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `aea90364.constant.771-13-i-secciones-minimas-mm2` | AEA 90364-7-771 (2006) | 771.13.I | - | `aea_tables.json#/constantes/771.13.I_secciones_minimas_mm2` | mm2 | norm | medium | pending | duplicated literal: aea90364.criterion.min-section-lighting-mm2 (1.5), aea90364.criterion.min-section-sockets-mm2 (2.5) |
| `aea90364.constant.771-13-pen-minima-mm2` | AEA 90364-7-771 (2006) | 771.13 | - | `aea_tables.json#/constantes/771.13_pen_minima_mm2` | mm2 | norm | medium | pending | - |
| `aea90364.constant.771-19-ii-k-adiabatico` | AEA 90364-7-771 (2006) | 771.19.II | - | `aea_tables.json#/constantes/771.19.II_k_adiabatico` | A*s^0.5/mm2 | norm | medium | pending | one lookup (ENG-14, decision D12): cable_thermal.k_material calls aea_conductors.k_adiabatico_771; PVC above 300 mm2 uses Cu 103 / Al 68 when the section is passed (None behaves as up to 300 mm2) |
| `aea90364.constant.771-19-iv-caida-unitaria-va-km` | AEA 90364-7-771 (2006) | 771.19.IV | - | `aea_tables.json#/constantes/771.19.IV_caida_unitaria_va_km` | V/(A*km) | norm | medium | pending | - |
| `aea90364.constant.771-19-gdc-comun` | AEA 90364-7-771 (2006) | 771.19 | - | `aea_tables.json#/constantes/771.19_gdc_comun` | - | norm | medium | pending | no clause in data beyond 771.19 (table not named) |
| `aea90364.constant.771-19-gdc-arranque` | AEA 90364-7-771 (2006) | 771.19 | - | `aea_tables.json#/constantes/771.19_gdc_arranque` | - | norm | medium | pending | no clause in data beyond 771.19 (table not named) |
| `aea90364.constant.771-19-limites-caida-pct` | AEA 90364-7-771 (2006) | 771.19 | - | `aea_tables.json#/constantes/771.19_limites_caida_pct` | % | norm | medium | pending | duplicated literal: aea90364.criterion.vd-sectional-pct (1), aea90364.criterion.vd-lighting-sockets-pct (3), aea90364.criterion.vd-motors-pct (5); motor_arranque 15 also in constantes/fuerza_motriz/caida_arranque_max_pct |
| `aea90364.constant.771-18-iii-tiempos-desconexion-s` | AEA 90364-7-771 (2006) | 771.18.III | - | `aea_tables.json#/constantes/771.18.III_tiempos_desconexion_s` | s | norm | medium | pending | the official table number must be verified: the JSON key says 771.18.III, the engine code used to say Tabla 771.18.I (code comment fixed in ENG-14; one table, no copy in code) |
| `aea90364.constant.771-18-t-seccional-s` | AEA 90364-7-771 (2006) | 771.18 | - | `aea_tables.json#/constantes/771.18_t_seccional_s` | s | norm | medium | pending | TN changed from 5 s to 2 s by owner decision D25 (ENG-14, 2026-11-10); up to 5 s only with selectivity: see 771.18_t_seccional_selectividad_tn_s |
| `aea90364.constant.771-18-ra-max-ohm` | AEA 90364-7-771 (2006) | 771.18 | - | `aea_tables.json#/constantes/771.18_ra_max_ohm` | ohm | norm | medium | pending | - |
| `aea90364.constant.771-18-ul-v` | AEA 90364-7-771 (2006) | 771.18 | - | `aea_tables.json#/constantes/771.18_ul_v` | V | norm | medium | pending | decision D11: UL = 24 V (general) is the only one used by the engine for the TT limit; col1 (50 V) is read only when a function asks for it explicitly |
| `aea90364.constant.770-coef-grado-771` | - | - | - | `aea_tables.json#/constantes/770_coef_grado_771` | - | norm | low | pending | no clause in data (key names only part 770); norm edition not stated in data |
| `aea90364.constant.770-coef-circuitos` | - | - | - | `aea_tables.json#/constantes/770_coef_circuitos` | - | norm | low | pending | no clause in data (key names only part 770); norm edition not stated in data |
| `aea90364.constant.proteccion-k-max-i2-iz` | - | - | - | `aea_tables.json#/constantes/proteccion_k_max_i2_iz` | - | norm | low | pending | no clause in data; norm part not stated in data (meta says Parte 4) |
| `aea90364.constant.proteccion-k2-convencional` | - | - | - | `aea_tables.json#/constantes/proteccion_k2_convencional` | - | norm | low | pending | no clause in data; norm part not stated in data (meta says Parte 4) |
| `aea90364.constant.proteccion-k1-no-disparo` | - | - | - | `aea_tables.json#/constantes/proteccion_k1_no_disparo` | - | norm | low | pending | no clause in data; norm part not stated in data (meta says Parte 4) |
| `aea90364.constant.compensacion-reactiva` | - | - | - | `aea_tables.json#/constantes/compensacion_reactiva` | - | typical | low | pending | no clause in data |
| `aea90364.constant.descargas-atmosfericas` | - | - | - | `aea_tables.json#/constantes/descargas_atmosfericas` | - | typical | low | pending | no clause in data; norm not stated in data |
| `aea90364.constant.equipotencialidad-principal` | AEA 90364-5-54 (2006) | 544.1.1 | - | `aea_tables.json#/constantes/equipotencialidad_principal` | mm2 | norm | medium | pending | - |
| `aea90364.constant.impedancias-estandar` | - | - | - | `aea_tables.json#/constantes/impedancias_estandar` | ohm/km | typical | low | pending | no clause in data; norm not stated in data |
| `aea90364.constant.factores-demanda-sistema` | AEA 90364-7-771 (2006) | 771.9 | - | `aea_tables.json#/constantes/factores_demanda_sistema` | - | design-default | medium | pending | data says 771.9 gives no factor per load type: 1.0 until the project sets one |
| `aea90364.constant.fuerza-motriz` | AEA 90364-7-770 (2017) | 770.15.6 | - | `aea_tables.json#/constantes/fuerza_motriz` | % | typical | low | pending | mixed content: caida_arranque_max_pct (15) cites the norm, the rest is typical; duplicated literal: 15 also in constantes/771.19_limites_caida_pct/motor_arranque |
| `aea90364.constant.respaldo-grupo-ups` | - | - | - | `aea_tables.json#/constantes/respaldo_grupo_ups` | kVA | typical | low | pending | no clause in data |

## aea90364 / criteria

Archivo: `harness/src/engines/calculation/aea90364/src/epc_aea90364/norm_register/criteria.json` (18 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `aea90364.criterion.nominal-voltage-v` | - | - | - | `design-criteria.json#/criteria/0` | V | design-default | low | pending (revision: approved) | no clause in data; criteria file is marked validated=false |
| `aea90364.criterion.frequency-hz` | - | - | - | `design-criteria.json#/criteria/1` | Hz | design-default | low | pending (revision: approved) | no clause in data; criteria file is marked validated=false |
| `aea90364.criterion.socket-height-m` | - | - | - | `design-criteria.json#/criteria/2` | m | design-default | low | pending (revision: approved) | no clause in data; criteria file is marked validated=false |
| `aea90364.criterion.switch-height-m` | - | - | - | `design-criteria.json#/criteria/3` | m | design-default | low | pending (revision: approved) | no clause in data; criteria file is marked validated=false |
| `aea90364.criterion.board-height-m` | - | - | - | `design-criteria.json#/criteria/4` | m | design-default | low | pending (revision: approved) | no clause in data; criteria file is marked validated=false |
| `aea90364.criterion.vd-sectional-pct` | - | - | - | `design-criteria.json#/criteria/5` | % | design-default | low | pending (revision: approved) | no clause in data; criteria file is marked validated=false; duplicated literal: default also stated by aea90364.constant.771-19-limites-caida-pct |
| `aea90364.criterion.vd-lighting-sockets-pct` | - | - | - | `design-criteria.json#/criteria/6` | % | design-default | low | pending (revision: approved) | no clause in data; criteria file is marked validated=false; duplicated literal: default also stated by aea90364.constant.771-19-limites-caida-pct |
| `aea90364.criterion.vd-motors-pct` | - | - | - | `design-criteria.json#/criteria/7` | % | design-default | low | pending (revision: approved) | no clause in data; criteria file is marked validated=false; duplicated literal: default also stated by aea90364.constant.771-19-limites-caida-pct |
| `aea90364.criterion.conductor-material` | - | - | - | `design-criteria.json#/criteria/8` | - | design-default | low | pending (revision: approved) | no clause in data; criteria file is marked validated=false |
| `aea90364.criterion.insulation` | - | - | - | `design-criteria.json#/criteria/9` | - | design-default | low | pending (revision: approved) | no clause in data; criteria file is marked validated=false |
| `aea90364.criterion.min-section-lighting-mm2` | - | - | - | `design-criteria.json#/criteria/10` | mm² | design-default | low | pending (revision: approved) | no clause in data; criteria file is marked validated=false; duplicated literal: default also stated by aea90364.constant.771-13-i-secciones-minimas-mm2 |
| `aea90364.criterion.min-section-sockets-mm2` | - | - | - | `design-criteria.json#/criteria/11` | mm² | design-default | low | pending (revision: approved) | no clause in data; criteria file is marked validated=false; duplicated literal: default also stated by aea90364.constant.771-13-i-secciones-minimas-mm2 |
| `aea90364.criterion.rcd-sensitivity-ma` | - | - | - | `design-criteria.json#/criteria/12` | mA | design-default | low | pending (revision: approved) | no clause in data; criteria file is marked validated=false |
| `aea90364.criterion.board-spare-pct` | - | - | - | `design-criteria.json#/criteria/13` | % | design-default | low | pending (revision: approved) | no clause in data; criteria file is marked validated=false |
| `aea90364.criterion.raceway-fill-max-pct` | - | - | - | `design-criteria.json#/criteria/14` | % | design-default | low | pending (revision: approved) | no clause in data; criteria file is marked validated=false |
| `aea90364.criterion.ambient-temp-c` | - | - | - | `design-criteria.json#/criteria/15` | °C | design-default | low | pending | no clause in data; criteria file is marked validated=false; duplicated literal: default also stated by aea90364.table.771-16-i |
| `aea90364.criterion.soil-temp-c` | - | - | - | `design-criteria.json#/criteria/16` | °C | design-default | low | pending | no clause in data; criteria file is marked validated=false; duplicated literal: default also stated by aea90364.table.771-16-v |
| `aea90364.criterion.soil-resistivity-kmw` | - | - | - | `design-criteria.json#/criteria/17` | K·m/W | design-default | low | pending | no clause in data; criteria file is marked validated=false; duplicated literal: default also stated by aea90364.table.771-16-v |

## aea90364 / jurisdiction

Archivo: `harness/src/engines/calculation/aea90364/src/epc_aea90364/norm_register/jurisdiction.json` (2 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `aea90364.jurisdiction.ar.voltages_lv` | - | - | - | `jurisdiction.json#/voltages_lv` | V | norm | low | pending | 230/400 here vs nominal_voltage_v options 220/380/400 (default 380) in aea90364 design-criteria.json: conflicting values; no norm or clause cited |
| `aea90364.jurisdiction.ar.frequency_hz` | - | - | - | `jurisdiction.json#/frequency_hz` | Hz | norm | medium | pending | design-criteria frequency_hz allows 50 or 60 (default 50): duplicate |

## aea90364 / tables

Archivo: `harness/src/engines/calculation/aea90364/src/epc_aea90364/norm_register/tables.json` (16 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `aea90364.table.771-16-i` | AEA 90364-7-771 (2006) | 771.16.I | PDF 105 | `aea_tables.json#/tablas_capacidad/771.16.I` | A | norm | medium | pending | no printed page in data (PDF page only) |
| `aea90364.table.771-16-iii` | AEA 90364-7-771 (2006) | 771.16.III | PDF 107 | `aea_tables.json#/tablas_capacidad/771.16.III` | A | norm | medium | pending | no printed page in data (PDF page only) |
| `aea90364.table.771-16-v` | AEA 90364-7-771 (2006) | 771.16.V | PDF 113 | `aea_tables.json#/tablas_capacidad/771.16.V` | A | norm | medium | pending | no printed page in data (PDF page only) |
| `aea90364.table.771-16-vi` | AEA 90364-7-771 (2006) | 771.16.VI | PDF 115 | `aea_tables.json#/tablas_capacidad/771.16.VI` | A | norm | medium | pending | no printed page in data (PDF page only) |
| `aea90364.table.771-16-viii` | AEA 90364-7-771 (2006) | 771.16.VIII | PDF 121 | `aea_tables.json#/tablas_capacidad/771.16.VIII` | A | norm | medium | pending | no printed page in data (PDF page only) |
| `aea90364.table.771-16-xi` | AEA 90364-7-771 (2006) | 771.16.XI | PDF 121 | `aea_tables.json#/tablas_capacidad/771.16.XI` | A | norm | medium | pending | no printed page in data (PDF page only) |
| `aea90364.table.771-16-ii-a` | AEA 90364-7-771 (2006) | 771.16.II.a | PDF 106 | `aea_tables.json#/factores_correccion/771.16.II.a` | - | norm | medium | pending | no printed page in data (PDF page only) |
| `aea90364.table.771-16-ii-b` | AEA 90364-7-771 (2006) | 771.16.II.b | PDF 106 | `aea_tables.json#/factores_correccion/771.16.II.b` | - | norm | medium | pending | no printed page in data (PDF page only) |
| `aea90364.table.771-16-iv` | AEA 90364-7-771 (2006) | 771.16.IV | PDF 110 | `aea_tables.json#/factores_correccion/771.16.IV` | - | norm | medium | pending | no printed page in data (PDF page only) |
| `aea90364.table.771-16-vii-a` | AEA 90364-7-771 (2006) | 771.16.VII.a | PDF 119 | `aea_tables.json#/factores_correccion/771.16.VII.a` | - | norm | medium | pending | no printed page in data (PDF page only) |
| `aea90364.table.771-16-vii-b` | AEA 90364-7-771 (2006) | 771.16.VII.b | PDF 119 | `aea_tables.json#/factores_correccion/771.16.VII.b` | - | norm | medium | pending | no printed page in data (PDF page only) |
| `aea90364.table.771-16-vii-c` | AEA 90364-7-771 (2006) | 771.16.VII.c | PDF 120 | `aea_tables.json#/factores_correccion/771.16.VII.c` | - | norm | medium | pending | no printed page in data (PDF page only) |
| `aea90364.table.771-16-vii-d1` | AEA 90364-7-771 (2006) | 771.16.VII.d1 | PDF 120 | `aea_tables.json#/factores_correccion/771.16.VII.d1` | - | norm | medium | pending | no printed page in data (PDF page only) |
| `aea90364.table.771-16-vii-d2` | AEA 90364-7-771 (2006) | 771.16.VII.d2 | PDF 120 | `aea_tables.json#/factores_correccion/771.16.VII.d2` | - | norm | medium | pending | no printed page in data (PDF page only) |
| `aea90364.table.771-16-ix` | AEA 90364-7-771 (2006) | 771.16.IX | PDF 121 | `aea_tables.json#/factores_correccion/771.16.IX` | - | norm | medium | pending | no printed page in data (PDF page only) |
| `aea90364.table.771-16-x` | AEA 90364-7-771 (2006) | 771.16.X | PDF 121 | `aea_tables.json#/factores_correccion/771.16.X` | - | norm | medium | pending | no printed page in data (PDF page only) |

## arch / sheet_iram

Archivo: `harness/src/engines/cad/arch/src/epc_arch/norm_register/sheet_iram.json` (1 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `arch.code.gap` | - | - | - | `5.0` | mm | design-default | low | pending | duplicates drawing plan_sheet.GAP (5.0): duplicates a value defined elsewhere (ADR-0012 single source); no clause |

## datasheets / params

Archivo: `harness/src/engines/procurement/datasheets/src/epc_datasheets/norm_register/params.json` (4 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `datasheets.params.catalog_abb_breakers` | - | - | - | `breakers.json#/products` | A, kA, V | convention | low | pending | no clause: manufacturer catalog (unverified); every product has status unverified and a source URL to check |
| `datasheets.params.catalog_schneider_electric_breakers` | - | - | - | `breakers.json#/products` | A, kA, V | convention | low | pending | no clause: manufacturer catalog (unverified); every product has status unverified and a source URL to check |
| `datasheets.params.catalog_siemens_breakers` | - | - | - | `breakers.json#/products` | A, kA, V | convention | low | pending | no clause: manufacturer catalog (unverified); every product has status unverified and a source URL to check |
| `datasheets.params.catalog_prysmian_cables` | - | - | - | `cables.json#/products` | - | convention | low | pending | no clause: manufacturer catalog (unverified); every product has status unverified and a source URL to check |

## draw / iram_sheet

Archivo: `harness/src/engines/cad/draw/src/epc_draw/norm_register/iram_sheet.json` (12 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `titleblock.code.formatos` | IRAM 4504 (Manual IRAM Ed. XXVII (as cited in code docstring)) | 2.3.1, 2.3.2, 2.3.3, fig. 5, fig. 6 | - | `{"A0": [1189, 841, 20, 20, 12, 6], "A1": [841, 594, 25, 1...` | mm; columns x rows | norm | medium | pending | A0 12x6 and A2 6x3 coordinate grids are derived by the code authors (module ~99 x 140), only A1 8x4 and A3 4x2 are as in fig. 6; A0 margin 20 on four sides (fig. 16), A1-A4 left 25 and 10 elsewhere; A4 has no coordinates; entry is portrait (210x297) while others are landscape; engine/drawing plan_sheet.FORMATS repeats the format names |
| `titleblock.code.w_rec_w_util_w_cent` | IRAM 4502 / IRAM 4504 (Manual IRAM Ed. XXVII (as cited in code docstring)) | 4502 line A group d (recuadro); 4504 2.4.1 (centring) | - | `{"W_REC": 1.0, "W_UTIL": 0.5, "W_CENT": 0.5}` | mm | norm | medium | pending | W_UTIL has no clause in the code comment; layout.DEFAULT_PENS repeats 1.0/0.5 (frame/zone): duplicates a value defined elsewhere (ADR-0012 single source) |
| `titleblock.code.w_rotulo` | IRAM 4508 (Manual IRAM Ed. XXVII (as cited in code docstring)) | fig. 2 | - | `{"W_08": 0.8, "W_04": 0.4, "W_02": 0.2}` | mm | norm | medium | pending | layout.DEFAULT_PENS repeats outline 0.8 / cell 0.4 / fine 0.2: duplicates a value defined elsewhere (ADR-0012 single source) |
| `titleblock.code.bloque_rotulo_dim` | IRAM 4508 (Manual IRAM Ed. XXVII (as cited in code docstring)) | fig. 2 (175 x 51), fig. 3 (175 x 21.5) | - | `{"RW": 175, "RH": 51, "MH": 21.5}` | mm | norm | medium | pending | layout.DEFAULT_BLOCK repeats 175/51/21.5: duplicates a value defined elsewhere (ADR-0012 single source) |
| `titleblock.code.cx_columnas` | IRAM 4508 (Manual IRAM Ed. XXVII (as cited in code docstring)) | fig. 2 (columns 26/20/10/19/45/55) | - | `[0, 26, 46, 56, 75, 120, 175]` | mm | norm | medium | pending | cell geometry inside the block (rows, cell positions) is hard-coded in dibujar_rotulo and not registered individually |
| `titleblock.code.xv` | IRAM 4508 (Manual IRAM Ed. XXVII (as cited in code docstring)) | fig. 2 | - | `64` | mm | norm | medium | pending | - |
| `titleblock.code.t25` | IRAM 4503 (Manual IRAM Ed. XXVII (as cited in code docstring)) | - | - | `2.5` | mm | norm | low | pending | no clause in code beyond 'IRAM 4503' for capital height; text heights 2.5 / 1.8 here, 2.0 in layout.DEFAULT_TEXT block, 1.7 in dxf ALTURA_TEXTO_MM: inconsistent |
| `titleblock.code.lab` | IRAM 4508 (Manual IRAM Ed. XXVII (as cited in code docstring)) | fig. 2 | - | `1.8` | mm | norm | low | pending | see t25 text-height inconsistency |
| `titleblock.code.fr` | IRAM 4504 (Manual IRAM Ed. XXVII (as cited in code docstring)) | fig. 6 (not cited at the line) | - | `{"with_coordinates": 5, "without": 0}` | mm | norm | low | pending | value is conditional in code: 5 if the format has coordinates else 0; no clause cited at the definition |
| `titleblock.layout.default_pens` | IRAM 4502 / 4508 | - | - | `{"cut": 0.1, "frame": 1.0, "zone": 0.5, "outline": 0.8, "...` | mm | norm | medium | pending | no clause in layout.py; values repeat lamina_iram W_* constants: duplicates a value defined elsewhere (ADR-0012 single source) |
| `titleblock.layout.default_text` | - | - | - | `{"coordinates": 3.5, "block": 2.0}` | mm | design-default | low | pending | block text 2.0 vs 2.5/1.8 in lamina_iram and 1.7 in dxf; no clause |
| `titleblock.layout.default_block` | IRAM 4508 | - | - | `{"width": 175, "height": 51, "modifications_height": 21.5}` | mm | norm | medium | pending | repeats RW/RH/MH of lamina_iram: duplicates a value defined elsewhere (ADR-0012 single source); no clause in layout.py |

## draw / svg_to_dxf

Archivo: `harness/src/engines/cad/draw/src/epc_draw/norm_register/svg_to_dxf.json` (5 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `dxf.code.altura_texto_mm` | - | - | - | `1.7` | mm | design-default | low | pending | 1.7 mm vs 2.0 (layout.DEFAULT_TEXT block, FS_ROTULO comment says 2 mm) and 2.5/1.8 in lamina_iram; no clause |
| `dxf.code.fs_rotulo` | - | - | - | `2.778` | svg units | convention | low | pending | comment says it is the font-size generated for 2 mm; ratio 2.778/2 differs from FS_LEGAL/ALTURA_LEGAL 1.528/1.0 |
| `dxf.code.altura_legal_mm` | - | - | - | `1.0` | mm | design-default | low | pending | no clause |
| `dxf.code.px_por_mm` | - | - | - | `3.77953` | px/mm | physics | medium | pending | exact 96/25.4 = 3.7795276; code uses 3.779530 |
| `dxf.layers.lineweights` | - | - | - | `[0.0, 0.05, 0.09, 0.13, 0.15, 0.18, 0.2, 0.25, 0.3, 0.35,...` | mm | convention | medium | pending | layer names (e.g. '0' used for all converted entities) are not registered |

## drawing / plan_sheet

Archivo: `harness/src/engines/cad/drawing/src/epc_drawing/norm_register/plan_sheet.json` (4 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `drawing.code.standard_scales` | - | - | - | `[1, 2, 5, 10, 20, 25, 50, 75, 100, 125, 150, 200, 250, 50...` | 1:n | convention | low | pending | no clause: code does not cite the scale standard (IRAM 4505?); list includes 1:75, 1:125, 1:150, 1:1500, 1:2000, 1:5000: check which are standard |
| `drawing.code.formats` | - | - | - | `["A0", "A1", "A2", "A3", "A4"]` | - | convention | medium | pending | duplicates titleblock FORMATOS keys (names only): duplicates a value defined elsewhere (ADR-0012 single source) |
| `drawing.code.gap` | - | - | - | `5.0` | mm | design-default | low | pending | duplicates arch sheet_iram.GAP (5.0): duplicates a value defined elsewhere (ADR-0012 single source); no clause |
| `drawing.code.unit_mm` | - | - | - | `{"4": 1.0, "5": 10.0, "6": 1000.0}` | mm per unit | physics | medium | pending | codes 4/5/6 = mm/cm/m of DXF $INSUNITS |

## hvac / constants

Archivo: `harness/src/engines/calculation/hvac/src/epc_hvac/norm_register/constants.json` (3 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `hvac.code.air_sensible_w_per_ls_k` | - | - | - | `1.23` | W per (L/s) per K | physics | medium | pending | 1.23 vs RHO_AIRE x CP_AIRE = 1.2 x 1.006 = 1.207 in harness/src/engines/calculation/aea90364 hvac_airflow.py (both marked [VERIFICAR] there): about 2 % apart, two sources |
| `hvac.code.air_latent_w_per_ls_kgkg` | - | - | - | `3010.0` | W per (L/s) per kg/kg | physics | medium | pending | aea90364 hvac_airflow has no latent constant to compare; 3010 implies rho 1.2 x hfg ~2508 kJ/kg |
| `hvac.code.watts_per_refrigeration_ton` | - | - | - | `3516.85` | W/TR | convention | medium | pending | - |

## hvac / typical

Archivo: `harness/src/engines/calculation/hvac/src/epc_hvac/norm_register/typical.json` (20 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `hvac.typical.params.person_sensible_w` | - | - | - | `typical.json#/params/person_sensible_w` | W | typical | low | pending | file says nothing here is a standard value; no clause |
| `hvac.typical.params.person_latent_w` | - | - | - | `typical.json#/params/person_latent_w` | W | typical | low | pending | file says nothing here is a standard value; no clause |
| `hvac.typical.params.default_infiltration_ach` | - | - | - | `typical.json#/params/default_infiltration_ach` | ach | typical | low | pending | file says nothing here is a standard value; no clause |
| `hvac.typical.params.default_lighting_use_factor` | - | - | - | `typical.json#/params/default_lighting_use_factor` | ratio | typical | low | pending | file says nothing here is a standard value; no clause |
| `hvac.typical.params.typical_cop` | - | - | - | `typical.json#/params/typical_cop` | - | typical | low | pending | file says nothing here is a standard value; no clause |
| `hvac.typical.solar.n` | - | - | - | `typical.json#/solar/N` | W/m2 | typical | low | pending | no clause or latitude; Argentine (southern hemisphere) orientation vs values to check |
| `hvac.typical.solar.ne` | - | - | - | `typical.json#/solar/NE` | W/m2 | typical | low | pending | no clause or latitude |
| `hvac.typical.solar.e` | - | - | - | `typical.json#/solar/E` | W/m2 | typical | low | pending | no clause or latitude |
| `hvac.typical.solar.se` | - | - | - | `typical.json#/solar/SE` | W/m2 | typical | low | pending | no clause or latitude |
| `hvac.typical.solar.s` | - | - | - | `typical.json#/solar/S` | W/m2 | typical | low | pending | no clause or latitude; Argentine (southern hemisphere) orientation vs values to check |
| `hvac.typical.solar.sw` | - | - | - | `typical.json#/solar/SW` | W/m2 | typical | low | pending | no clause or latitude |
| `hvac.typical.solar.w` | - | - | - | `typical.json#/solar/W` | W/m2 | typical | low | pending | no clause or latitude |
| `hvac.typical.solar.nw` | - | - | - | `typical.json#/solar/NW` | W/m2 | typical | low | pending | no clause or latitude |
| `hvac.typical.solar.h` | - | - | - | `typical.json#/solar/H` | W/m2 | typical | low | pending | no clause or latitude |
| `hvac.typical.ventilation.office` | - | - | - | `typical.json#/ventilation/office` | L/s per person; L/s per m2 | typical | low | pending | no clause; values resemble ASHRAE 62.1 style rates but no norm is cited |
| `hvac.typical.ventilation.meeting_room` | - | - | - | `typical.json#/ventilation/meeting_room` | L/s per person; L/s per m2 | typical | low | pending | no clause; values resemble ASHRAE 62.1 style rates but no norm is cited |
| `hvac.typical.ventilation.retail` | - | - | - | `typical.json#/ventilation/retail` | L/s per person; L/s per m2 | typical | low | pending | no clause; values resemble ASHRAE 62.1 style rates but no norm is cited |
| `hvac.typical.ventilation.classroom` | - | - | - | `typical.json#/ventilation/classroom` | L/s per person; L/s per m2 | typical | low | pending | no clause; values resemble ASHRAE 62.1 style rates but no norm is cited |
| `hvac.typical.ventilation.restaurant` | - | - | - | `typical.json#/ventilation/restaurant` | L/s per person; L/s per m2 | typical | low | pending | no clause; values resemble ASHRAE 62.1 style rates but no norm is cited |
| `hvac.typical.ventilation.default` | - | - | - | `typical.json#/ventilation/default` | L/s per person; L/s per m2 | typical | low | pending | no clause; values resemble ASHRAE 62.1 style rates but no norm is cited |

## lighting / d351_79

Archivo: `harness/src/engines/calculation/lighting/src/epc_lighting/norm_register/d351_79.json` (2 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `lighting.standard.d351-79.edition` | Decreto 351/79 (Ley 19587), Cap. 12, Anexo IV | - | - | `D351-79.json#/edition` | - | norm | low | pending | edition is 'to verify' (file says '1979 (texto vigente a verificar)'); based_on says IRAM-AADL J 20-06 (not cited anywhere else); industrial rows of Tabla 2 not loaded |
| `lighting.rules.d351-79.rule_set` | Decreto 351/79 (Ley 19587) | Anexo IV, Tabla 2 | - | `D351-79.rules.json#/rules` | lx | norm | medium | pending | rules carry clause text but no edition and no page; second set of levels exists in data/levels.json (European norm via teaching article) - two sets of levels coexist; rules auto-indexed individually by the validator; industrial rows of Tabla 2 not loaded |

## lighting / data

Archivo: `harness/src/engines/calculation/lighting/src/epc_lighting/norm_register/data.json` (12 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `lighting.data.levels` | UNE-EN 12464-1:2003 (quoted by UPV lumen-method article) and ICARO manual (2003) | tables 6.2.1-6.2.3 (education rows); ICARO I.1 2.1 (task/room rows) | - | `levels.json#/activities` | lx (UGRL, Ra dimensionless) | teaching | low | pending | European norm via a teaching article, not an Argentine norm; D351-79 rules also give levels: two sets of levels, not reconciled (e.g. classroom/office values differ in source); ICARO rows give no norm and no UGR/Ra; edition 2003 is superseded by later EN 12464-1 editions |
| `lighting.data.reflectances.defaults` | UPV lumen-method article (no standard) | sentence after table 4 | - | `reflectances.json#/defaults` | ratio 0-1 | teaching | low | pending | rule of thumb from a teaching article, not a norm |
| `lighting.data.reflectances.materials` | UPV lumen-method article | table 4 | - | `reflectances.json#/materials` | ratio 0-1 | teaching | low | pending | teaching article table, 30 materials; midpoint of range used with reduced confidence (0.7) |
| `lighting.data.maintenance.interior` | UPV lumen-method article | table 6 | - | `maintenance.json#/interior` | ratio | typical | low | pending | annual cleaning assumed; typical, not normative |
| `lighting.data.maintenance.interior_range` | UNAC chapter III | - | - | `maintenance.json#/interior_range` | ratio | typical | low | pending | UNAC chapter III cited, no section/table number |
| `lighting.data.maintenance.exterior` | UNAC chapter III | section 5 | - | `maintenance.json#/exterior` | ratio | typical | low | pending | typical, not normative |
| `lighting.data.spacing.by_room_height` | UPV lumen-method article | table 7 | - | `spacing.json#/by_room_height` | multiple of h | teaching | low | pending | rows 'extensive 6-10' and 'semi-extensive 4-6' have the same ratio 1.5 and two rows are called 'extensive': check against the source table |
| `lighting.data.lighting_systems.systems` | UPV lumen-method article; UNAC chapter III | UPV tables 1-3; UNAC 1 and 2.6 | - | `lighting_systems.json#/systems` | multiple of h | teaching | low | pending | spacing_ratio null where sources give none |
| `lighting.data.lighting_systems.suspension_rules` | UPV lumen-method article | table 2 | - | `lighting_systems.json#/suspension_rules` | fraction | teaching | low | pending | indirect auto_min 0.8 vs auto_optimal 0.75: minimum is larger than optimal, check source |
| `lighting.data.cu_generic` | UPV lumen-method article | table 5 | - | `cu_generic.json#/cu_table` | percent | illustrative | low | pending | manufacturer table of one luminaire used as generic fallback (warning, confidence 0.4); values above 100 appear; orientation of 'values' (rows by k or by reflectance set) is not stated in the file: verify the engine reads it as in the source |
| `lighting.data.luminaires` | - | - | - | `luminaires.json#/luminaires` | lm, W, cd/klm | illustrative | low | pending | flux and power are typical of the kind, not of a maker; flagged illustrative |
| `lighting.data.room_types` | - | - | - | `room_types.json#/rules` | m (default height); activity ids of lighting.data.levels | design-default | low | pending | no clause: which activity a room is lit for, and the 3.0 m ceiling height, are design defaults; adds no illuminance value: the lux are those of lighting.data.levels |

## lighting / params

Archivo: `harness/src/engines/calculation/lighting/src/epc_lighting/norm_register/params.json` (9 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `lighting.params.defaults.work_plane_height_m` | - | - | - | `params.json#/defaults/work_plane_height_m` | m | design-default | low | pending | no clause cited; params note says typical values are not normative |
| `lighting.params.defaults.area_beam_utilisation` | - | - | - | `params.json#/defaults/area_beam_utilisation` | ratio | design-default | low | pending | no clause; range 0.6-0.9 in beam_utilisation_range; source of 0.75 not cited |
| `lighting.params.beam_utilisation_range` | - | - | - | `params.json#/beam_utilisation_range` | ratio | design-default | low | pending | no clause |
| `lighting.params.cavity.rcr_factor` | - | - | - | `params.json#/cavity/rcr_factor` | - | physics | medium | pending | standard IES zonal-cavity definition; no clause cited |
| `lighting.params.conformity.direct_factor` | - | - | - | `params.json#/conformity/direct_factor` | ratio | design-default | low | pending | no clause; code says typical value to confirm with project standard |
| `lighting.params.uniformity_limits` | - | - | - | `params.json#/uniformity_limits` | ratio | design-default | low | pending | no clause; min/avg 1/3, max/avg 3, max/min 10 look like rules of thumb |
| `lighting.params.emergency` | EN 1838 (as recalled in code) | - | - | `params.json#/emergency` | lx, ratio, m | typical | low | pending | no clause: code says 'as recalled, EN 1838'; Argentine requirements not referenced |
| `lighting.params.point_grid` | - | - | - | `params.json#/point_grid` | m | design-default | low | pending | numerical setting; not a norm value |
| `lighting.params.photometry_max_output_ratio` | - | - | - | `params.json#/photometry_max_output_ratio` | ratio | design-default | low | pending | tolerance setting, no source |

## plan / params

Archivo: `harness/src/engines/cad/plan/src/epc_plan/norm_register/params.json` (4 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `plan.params.geometry.snap_tolerance_m` | - | - | - | `params.json#/geometry/snap_tolerance_m` | m | design-default | low | pending | algorithm setting, not a norm |
| `plan.params.coordination.story_height_m` | - | - | - | `params.json#/coordination/story_height_m` | m | design-default | low | pending | no source; project dependent |
| `plan.params.dxf.text_height_m` | - | - | - | `params.json#/dxf/text_height_m` | m (plan units) | design-default | low | pending | 0.15 m in plan units (was 0.25 m: labels ran into each other); no scale link, no IRAM 4503 text height cited |
| `plan.params.style` | - | - | - | `params.json#/style` | mm | design-default | low | pending | 0.25 mm line and 2.0 mm font; no IRAM 4502/4503 reference; sheet pens are in titleblock |

## plan / rules

Archivo: `harness/src/engines/cad/plan/src/epc_plan/norm_register/rules.json` (2 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `plan.clash.rules` | - | - | - | `clash_rules.json#/rules` | m | typical | low | pending | file says typical values, not a standard; 0.30 m electrical-to-sewer has no clause |
| `plan.knowledge.sanitaria_cloacas.pendiente_minima` | - | - | - | `rules.json#/rules/0/table` | % (diameter mm) | norm | low | pending | slope_pct values are all null: waiting for the sewer standard the owner provides; source norma/edicion/clausula empty: no clause |

## plan / typical_values

Archivo: `harness/src/engines/cad/plan/src/epc_plan/norm_register/typical_values.json` (8 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `plan.typical.sizing.cable_mm_by_section` | - | - | - | `typical_values.json#/sizing/cable_mm_by_section` | mm (section in mm2) | typical | low | pending | no clause: file says confirm against the standard and the catalogue; catalogue dependent; not a norm value |
| `plan.typical.sizing.conduit_mm` | - | - | - | `typical_values.json#/sizing/conduit_mm` | mm | typical | low | pending | no clause: file says confirm against the standard and the catalogue; list 16-110 mm; is it internal or nominal diameter? |
| `plan.typical.tray_catalogue` | - | - | - | `typical_values.json#/tray_catalogue` | mm | typical | low | pending | no clause: file says confirm against the standard and the catalogue |
| `plan.typical.sizing.tray_fill_max_pct` | - | - | - | `typical_values.json#/sizing/tray_fill_max_pct` | % | typical | low | pending | given by the owner (40 %, 'as the standard says'); no clause recorded: a person must confirm it against the standard |
| `plan.typical.occupancy.default_cable_mm` | - | - | - | `typical_values.json#/occupancy/default_cable_mm` | mm | typical | low | pending | no clause: file says confirm against the standard and the catalogue |
| `plan.typical.occupancy.tray_pct` | - | - | - | `typical_values.json#/occupancy/tray_pct` | % | typical | low | pending | no clause: file says confirm against the standard and the catalogue; 50 % here vs 40 % ocupacion_max_pct in aea90364 rules/bandejas.json (line 59); criterion raceway_fill_max_pct (default 40, range 40-60) is a separate value: three copies |
| `plan.typical.occupancy.conduit_pct` | - | - | - | `typical_values.json#/occupancy/conduit_pct` | % | typical | low | pending | no clause: file says confirm against the standard and the catalogue; 53/31/40 % (1 / 2 / many cables) vs 35 % in AEA rules canalizaciones (non-tabulated cases) and criterion raceway_fill_max_pct (default 40, range 40-60); the AEA rules refer to Tabla 771.12.IX for tabulated cases; compare these values with it |
| `plan.typical.design.families` | - | - | - | `typical_values.json#/design/families` | outlets; VA | typical | low | pending | no clause: file says confirm against the standard and the catalogue; TUG 15 outlets and TUE 1 outlet repeat receptacles circuits values (two copies); IUG 100 VA, IUE 10 VA, ACU 1500 VA, FMO 7500 VA per outlet are design assumptions |

## pv / typical

Archivo: `harness/src/engines/calculation/pv/src/epc_pv/norm_register/typical.json` (18 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `pv.typical.losses_pct.soiling` | - | - | - | `params.json#/losses_pct/soiling` | % | typical | low | pending | no clause; a common default of public PV yield tools, not a standard value |
| `pv.typical.losses_pct.shading` | - | - | - | `params.json#/losses_pct/shading` | % | typical | low | pending | no clause; a common default of public PV yield tools, not a standard value |
| `pv.typical.losses_pct.snow` | - | - | - | `params.json#/losses_pct/snow` | % | typical | low | pending | no clause; a common default of public PV yield tools, not a standard value |
| `pv.typical.losses_pct.mismatch` | - | - | - | `params.json#/losses_pct/mismatch` | % | typical | low | pending | no clause; a common default of public PV yield tools, not a standard value |
| `pv.typical.losses_pct.wiring` | - | - | - | `params.json#/losses_pct/wiring` | % | typical | low | pending | no clause; a common default of public PV yield tools, not a standard value |
| `pv.typical.losses_pct.connections` | - | - | - | `params.json#/losses_pct/connections` | % | typical | low | pending | no clause; a common default of public PV yield tools, not a standard value |
| `pv.typical.losses_pct.lid` | - | - | - | `params.json#/losses_pct/lid` | % | typical | low | pending | no clause; a common default of public PV yield tools, not a standard value |
| `pv.typical.losses_pct.nameplate_rating` | - | - | - | `params.json#/losses_pct/nameplate_rating` | % | typical | low | pending | no clause; a common default of public PV yield tools, not a standard value |
| `pv.typical.losses_pct.age` | - | - | - | `params.json#/losses_pct/age` | % | typical | low | pending | no clause; a common default of public PV yield tools, not a standard value |
| `pv.typical.losses_pct.availability` | - | - | - | `params.json#/losses_pct/availability` | % | typical | low | pending | no clause; a common default of public PV yield tools, not a standard value |
| `pv.typical.iam_ashrae_b0` | - | - | - | `params.json#/iam_ashrae_b0` | - | typical | low | pending | no clause; typical value for glass modules |
| `pv.typical.faiman.u0` | - | - | - | `params.json#/faiman/u0` | W/m2/K | typical | low | pending | no clause; typical open-rack value |
| `pv.typical.faiman.u1` | - | - | - | `params.json#/faiman/u1` | W s/m3/K | typical | low | pending | no clause; typical open-rack value |
| `pv.typical.inverter.eta_nom` | - | - | - | `params.json#/inverter/eta_nom` | 1 | typical | low | pending | no clause; typical of the PVWatts inverter curve |
| `pv.typical.inverter.eta_ref` | - | - | - | `params.json#/inverter/eta_ref` | 1 | typical | low | pending | no clause; reference point of the PVWatts inverter curve |
| `pv.typical.strings.isc_factor` | - | - | - | `params.json#/strings/isc_factor` | 1 | typical | low | pending | no clause; the 1.25 factor is a design convention to confirm against the adopted standard |
| `pv.typical.strings.policy` | - | - | - | `params.json#/strings/policy` | - | typical | low | pending | design choice, not a standard value |
| `pv.typical.solar_constant_w_m2` | - | - | - | `params.json#/solar_constant_w_m2` | W/m2 | typical | low | pending | physical constant used by the Spencer series; the value is a convention (1366.1) |

## receptacles / data

Archivo: `harness/src/engines/calculation/receptacles/src/epc_receptacles/norm_register/data.json` (21 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `receptacles.data.uses.general` | - | - | - | `uses.json#/uses/general` | outlets (per m2 / per m of perimeter / fixed) | typical | low | pending | no clause: 'typical value, to verify' |
| `receptacles.data.uses.office` | AEA 90364-7-771 (2006) | Tabla 771.8.VI (oficinas y locales) | - | `uses.json#/uses/office` | outlets (per m2 / per m of perimeter / fixed) | norm | medium | pending | uses.json note says only the warehouse perimeter rule comes from a norm clause and the rest is usual practice; this entry's source field says otherwise (or is 'typical value, to verify') |
| `receptacles.data.uses.classroom` | - | - | - | `uses.json#/uses/classroom` | outlets (per m2 / per m of perimeter / fixed) | typical | low | pending | no clause: 'typical value, to verify'; AEA rules tomacorrientes.escuelas_aulas_pizarron exists for classrooms; compare |
| `receptacles.data.uses.bedroom` | AEA 90364-7-771 (2006) | Tabla 771.8.III (viviendas) | - | `uses.json#/uses/bedroom` | outlets (per m2 / per m of perimeter / fixed) | norm | medium | pending | fixed count 3 ignores area: source text says three for 10-36 m2 and two if under 10 m2; larger than 36 m2 not covered; uses.json note says only the warehouse perimeter rule comes from a norm clause and the rest is usual practice; this entry's source field says otherwise (or is 'typical value, to verify') |
| `receptacles.data.uses.bedroom.small_room` | AEA 90364-7-771 (2006) | Tabla 771.8.III (viviendas) | - | `uses.json#/uses/bedroom/small_room` | outlets | norm | medium | pending | added by MIG-36i from the owner verdict of 2026-11-10 (r1_tomas_dormitorio_8m2: bedroom under 10 m2 gets 2 receptacles); the value 2 and the limit 10 m2 are the ones of the source text of the bedroom record; pending review, not verified against the printed table |
| `receptacles.data.uses.living` | AEA 90364-7-771 (2006) | Tabla 771.8.III (viviendas) | - | `uses.json#/uses/living` | outlets (per m2 / per m of perimeter / fixed) | norm | medium | pending | uses.json note says only the warehouse perimeter rule comes from a norm clause and the rest is usual practice; this entry's source field says otherwise (or is 'typical value, to verify') |
| `receptacles.data.uses.kitchen` | AEA 90364-7-771 (2006) | Tabla 771.8.III (viviendas) | - | `uses.json#/uses/kitchen` | outlets (per m2 / per m of perimeter / fixed) | norm | medium | pending | source text 'tres bocas más dos tomacorrientes (grado mínimo y medio)' is reduced to fixed 5; grade dependence lost; uses.json note says only the warehouse perimeter rule comes from a norm clause and the rest is usual practice; this entry's source field says otherwise (or is 'typical value, to verify') |
| `receptacles.data.uses.bathroom` | AEA 90364-7-771 (2006) | Tabla 771.8.III (viviendas) | - | `uses.json#/uses/bathroom` | outlets (per m2 / per m of perimeter / fixed) | norm | medium | pending | uses.json note says only the warehouse perimeter rule comes from a norm clause and the rest is usual practice; this entry's source field says otherwise (or is 'typical value, to verify') |
| `receptacles.data.uses.corridor` | AEA 90364-7-771 (2006) | Tabla 771.8.VI (oficinas y locales) y Tabla 771.8.III (viviendas) | - | `uses.json#/uses/corridor` | outlets (per m2 / per m of perimeter / fixed) | norm | low | pending | basis is perimeter with per_m 10 while the source text says one outlet per 5 m of length (10 m of perimeter only for narrow corridors): basis/divisor ambiguous; uses.json note says only the warehouse perimeter rule comes from a norm clause and the rest is usual practice; this entry's source field says otherwise (or is 'typical value, to verify'); MIG-36i: basis is now `length` with per_m 5 (from the source text) and the perimeter rule moved to `narrow`; both values pending review |
| `receptacles.data.uses.corridor.narrow` | AEA 90364-7-771 (2006) | Tabla 771.8.VI (oficinas y locales) y Tabla 771.8.III (viviendas) | - | `uses.json#/uses/corridor/narrow` | outlets | norm | low | pending | added by MIG-36i from the owner verdict of 2026-11-10 (r4_tomas_pasillo: narrow-corridor rule only when the normative classification applies explicitly); one outlet per 10 m of perimeter is taken from the source text of the corridor record; what counts as narrow is not defined in the data: the person states it with the room key `narrow`; pending review, not verified against the printed table |
| `receptacles.data.uses.workshop` | - | - | - | `uses.json#/uses/workshop` | outlets (per m2 / per m of perimeter / fixed) | typical | low | pending | no clause: 'typical value, to verify' |
| `receptacles.data.uses.warehouse` | AEA 90364-7-771 (2006) | 771.8.3.3.3.1 a 771.8.3.3.3.4 (via AEA rule tomacorrientes.deposito_perimetro) | - | `uses.json#/uses/warehouse` | outlets (per m2 / per m of perimeter / fixed) | norm | medium | pending | source field names the AEA rule id, not a clause; clause/page taken from harness/src/engines/calculation/aea90364 rules/tomacorrientes.json (p. 36 printed); the same rule adds one special-use outlet per 18 m (grades medium and above): not modelled here |
| `receptacles.data.uses.meeting_room` | AEA 90364-7-771 (2006) | Tabla 771.8.VI (oficinas y locales) | - | `uses.json#/uses/meeting_room` | outlets (per m2 / per m of perimeter / fixed) | norm | medium | pending | uses.json note says only the warehouse perimeter rule comes from a norm clause and the rest is usual practice; this entry's source field says otherwise (or is 'typical value, to verify') |
| `receptacles.data.uses.private_office` | AEA 90364-7-771 (2006) | Tabla 771.8.VI (oficinas y locales) | - | `uses.json#/uses/private_office` | outlets (per m2 / per m of perimeter / fixed) | norm | medium | pending | uses.json note says only the warehouse perimeter rule comes from a norm clause and the rest is usual practice; this entry's source field says otherwise (or is 'typical value, to verify') |
| `receptacles.data.uses.reception` | AEA 90364-7-771 (2006) | Tabla 771.8.VI (oficinas y locales) | - | `uses.json#/uses/reception` | outlets (per m2 / per m of perimeter / fixed) | norm | medium | pending | uses.json note says only the warehouse perimeter rule comes from a norm clause and the rest is usual practice; this entry's source field says otherwise (or is 'typical value, to verify') |
| `receptacles.data.mounting.771` | AEA 90364-7-771 (2006) | 771.8.6.2 | p. 44 | `uses.json#/mounting/771` | m | norm | medium | pending | clause/page taken from AEA rule tomacorrientes.altura_arista_inferior_771; the uses file only names the rule; min 0.15 m vs engine default 0.3 m (params.json) and criterion socket_height_m default 0.3 |
| `receptacles.data.mounting.770` | AEA 90364-7-770 (2017) | 770.7.2 | p. 13 | `uses.json#/mounting/770` | m | norm | medium | pending | clause/page taken from AEA rule tomacorrientes.altura_arista_inferior_770; different edition (2017) than the 771 data (2006) |
| `receptacles.data.mounting.wet_min_m` | - | - | - | `uses.json#/mounting/wet_min_m` | m | typical | low | pending | no clause in the data; AEA rules tomacorrientes.baldeado_771 / baldeado_770 exist; compare value |
| `receptacles.data.circuits.tug` | - | - | - | `uses.json#/circuits/TUG` | outlets | typical | low | pending | no clause: 'typical value, to verify'; plan typical_values design.families repeats max_outlets (TUG 15, TUE 1): two copies |
| `receptacles.data.circuits.tue` | - | - | - | `uses.json#/circuits/TUE` | outlets | typical | low | pending | no clause: 'typical value, to verify'; plan typical_values design.families repeats max_outlets (TUG 15, TUE 1): two copies |
| `receptacles.data.receptacles` | IRAM 2071 (named in titles) | - | - | `receptacles.json#/receptacles` | A, VA, m | illustrative | low | pending | rating/power are typical, flagged illustrative; TUE height_m 1.2 and power 2200 VA are typical values; other outlets 0.3 m; height 0.3 m vs mounting limits above |

## receptacles / params

Archivo: `harness/src/engines/calculation/receptacles/src/epc_receptacles/norm_register/params.json` (2 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `receptacles.params.corner_clearance_m` | - | - | - | `params.json#/corner_clearance_m` | m | design-default | low | pending | algorithm setting, no clause |
| `receptacles.params.default_mount_height_m` | - | - | - | `params.json#/default_mount_height_m` | m | design-default | low | pending | 0.3 m vs 771 min 0.15 and 770 band 0.2-0.3; criterion socket_height_m default 0.3 (aea90364 design-criteria): duplicated value |

## terminal_blocks / params

Archivo: `harness/src/engines/quality/terminal_blocks/src/epc_terminal_blocks/norm_register/params.json` (1 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `terminal_blocks.params.terminal_sizes` | - | - | - | `terminal_sizes.json#/terminal_sizes` | mm2, A | convention | low | pending | no clause: catalog/convention; values to verify against the chosen manufacturer catalog |

## transformer_sizing / params

Archivo: `harness/src/engines/calculation/transformer_sizing/src/epc_transformer_sizing/norm_register/params.json` (1 registros)

| id | norma | cláusula | página | valor / ubicación | unidad | procedencia | confianza | estado | problemas |
|---|---|---|---|---|---|---|---|---|---|
| `transformer_sizing.params.standard_ratings` | - | - | - | `standard_ratings.json#/ratings_kva` | kVA | convention | low | pending | no clause: convention; values to verify against the supply authority or manufacturer catalog |

## Sin cláusula

- `aea90364.code.aea_ampacity.alfa` (-; hand)
- `aea90364.code.aea_ampacity.default.ambiente_suelo_rho` (-; hand)
- `aea90364.code.aea_ampacity.factores.clase5` (AEA 90364-7-771; hand)
- `aea90364.code.aea_ampacity.r20_al_ohm_km` (IEC 60228; hand)
- `aea90364.code.aea_backup.arranque_defecto` (-; hand)
- `aea90364.code.aea_conductors.alfa_cu` (-; hand)
- `aea90364.code.aea_conductors.neutral_section.umbral` (-; hand)
- `aea90364.code.aea_demand.corriente_alimentador_motores.factor` (-; hand)
- `aea90364.code.aea_demand.factor_parallel` (IEC 60364-5-52; hand)
- `aea90364.code.aea_demand.requiere_trifasico` (-; hand)
- `aea90364.code.aea_demand.u_mono_v` (-; hand)
- `aea90364.code.aea_demand.u_tri_v` (-; hand)
- `aea90364.code.aea_earthing.resistencia_malla.sverak` (IEEE Std 80; hand)
- `aea90364.code.aea_export.du_aviso_pct` (-; hand)
- `aea90364.code.aea_export.serie_s_mm2` (-; hand)
- `aea90364.code.aea_feeder_report.default.tablero` (-; hand)
- `aea90364.code.aea_icc_decay.u_fmax` (AEA IT 90909-1; hand)
- `aea90364.code.aea_icc_factors.rigido_max_u_ratio` (AEA IT 90909-1; hand)
- `aea90364.code.aea_lightning.superficie_captacion.radio_3h` (IEC 62305-2; hand)
- `aea90364.code.aea_pipeline.c_max_bt` (AEA 90909-0; hand)
- `aea90364.code.aea_pipeline.c_min_bt` (AEA 90909-0; hand)
- `aea90364.code.aea_pipeline.default.ambient_c` (-; hand)
- `aea90364.code.aea_pipeline.default.fp` (-; hand)
- `aea90364.code.aea_pipeline.default.icc_ka` (-; hand)
- `aea90364.code.aea_pipeline.default.insulation` (-; hand)
- `aea90364.code.aea_pipeline.default.material` (-; hand)
- `aea90364.code.aea_pipeline.default.rcd_ma` (-; hand)
- `aea90364.code.aea_pipeline.default.rendimiento` (-; hand)
- `aea90364.code.aea_pipeline.default.rho_kmw` (-; hand)
- `aea90364.code.aea_pipeline.default.soil_c` (-; hand)
- `aea90364.code.aea_pipeline.default.temp_c` (-; hand)
- `aea90364.code.aea_pipeline.default.tension_v` (-; hand)
- `aea90364.code.aea_pipeline.du_acum_max_pct` (-; hand)
- `aea90364.code.aea_pipeline.hp_cv_w` (-; hand)
- `aea90364.code.aea_pipeline.hp_w` (-; hand)
- `aea90364.code.aea_pipeline.in_max_mcb_a` (IEC 60898-1; hand)
- `aea90364.code.aea_pipeline.margin_motor` (-; hand)
- `aea90364.code.aea_pipeline.serie_icu_ka` (-; hand)
- `aea90364.code.aea_pipeline.serie_in_a` (-; hand)
- `aea90364.code.aea_route.limites_validacion` (-; hand)
- `aea90364.code.aea_special_locations.b_lim_t` (AEA 90364-7-701; hand)
- `aea90364.code.aea_special_locations.i_cc_deteccion_ma` (AEA 90364-7-722; hand)
- `aea90364.code.aea_special_locations.i_min_load_multiple_to` (AEA 90364-7-722; hand)
- `aea90364.code.aea_special_locations.idn_diferencial_ev_ma` (AEA 90364-7-722; hand)
- `aea90364.code.aea_special_locations.load_multiple_complies.mitad` (AEA 90364-7-722; hand)
- `aea90364.code.aea_special_locations.max_outlets_load_multiple` (AEA 90364-7-722; hand)
- `aea90364.code.aea_special_locations.mu0` (-; hand)
- `aea90364.code.aea_special_locations.radio_zona2_m` (AEA 90364-7-701; hand)
- `aea90364.code.aea_voltage_drop.tension_defecto` (-; hand)
- `aea90364.code.board_figures.default.tablero` (-; hand)
- `aea90364.code.board_memo.curve_band.punto_2_55` (IEC 60898-1; hand)
- `aea90364.code.board_memo.curve_band.t_convencional` (IEC 60898-1 / IEC 60947-2; hand)
- `aea90364.code.board_memo.curve_band.tiempos_magneticos` (IEC 60898-1 / IEC 60947-2; hand)
- `aea90364.code.board_memo.curve_letter` (-; hand)
- `aea90364.code.board_memo.k_mag` (IEC 60898-1 / IEC 60947-2; hand)
- `aea90364.code.board_memo.ratio_termico` (-; hand)
- `aea90364.code.board_memo.selectividad.curva_aguas_arriba_defecto` (-; hand)
- `aea90364.code.board_memo.u0_v` (-; hand)
- `aea90364.code.cable_thermal.t_adiabatico_max_s` (IEC 60364-4-43; hand)
- `aea90364.code.cable_thermal.t_corto_s` (IEC 60364-4-43; hand)
- `aea90364.code.conductor_selection.cli.fp` (-; hand)
- `aea90364.code.grouping.default.max_circuits` (-; hand)
- `aea90364.code.grouping.default.max_ib_a` (-; hand)
- `aea90364.code.grouping.default.tablero` (-; hand)
- `aea90364.code.hazen_williams.constante_hw` (NFPA 13; hand)
- `aea90364.code.hazen_williams.exp_d` (NFPA 13; hand)
- `aea90364.code.hazen_williams.exp_q` (NFPA 13; hand)
- `aea90364.code.hazen_williams.g` (-; hand)
- `aea90364.code.hazen_williams.rho_agua` (-; hand)
- `aea90364.code.hvac_airflow.cp_aire` (ASHRAE Fundamentals; hand)
- `aea90364.code.hvac_airflow.rho_aire` (ASHRAE Fundamentals; hand)
- `aea90364.code.short_circuit.c_max_bt_tol_10` (IEC 60909-0; hand)
- `aea90364.code.short_circuit.temp_min_c` (IEC 60909-0; hand)
- `aea90364.code.short_circuit.umbral_motores_despreciable` (IEC 60909-0; hand)
- `aea90364.code.short_circuit.xr_red_defecto` (IEC 60909-0; hand)
- `aea90364.code.system_voltage.u0_380` (-; hand)
- `aea90364.constant.770-coef-circuitos` (-; hand)
- `aea90364.constant.770-coef-grado-771` (-; hand)
- `aea90364.constant.compensacion-reactiva` (-; hand)
- `aea90364.constant.descargas-atmosfericas` (-; hand)
- `aea90364.constant.impedancias-estandar` (-; hand)
- `aea90364.constant.proteccion-k-max-i2-iz` (-; hand)
- `aea90364.constant.proteccion-k1-no-disparo` (-; hand)
- `aea90364.constant.proteccion-k2-convencional` (-; hand)
- `aea90364.constant.respaldo-grupo-ups` (-; hand)
- `aea90364.criterion.ambient-temp-c` (-; hand)
- `aea90364.criterion.board-height-m` (-; hand)
- `aea90364.criterion.board-spare-pct` (-; hand)
- `aea90364.criterion.conductor-material` (-; hand)
- `aea90364.criterion.frequency-hz` (-; hand)
- `aea90364.criterion.insulation` (-; hand)
- `aea90364.criterion.min-section-lighting-mm2` (-; hand)
- `aea90364.criterion.min-section-sockets-mm2` (-; hand)
- `aea90364.criterion.nominal-voltage-v` (-; hand)
- `aea90364.criterion.raceway-fill-max-pct` (-; hand)
- `aea90364.criterion.rcd-sensitivity-ma` (-; hand)
- `aea90364.criterion.socket-height-m` (-; hand)
- `aea90364.criterion.soil-resistivity-kmw` (-; hand)
- `aea90364.criterion.soil-temp-c` (-; hand)
- `aea90364.criterion.switch-height-m` (-; hand)
- `aea90364.criterion.vd-lighting-sockets-pct` (-; hand)
- `aea90364.criterion.vd-motors-pct` (-; hand)
- `aea90364.criterion.vd-sectional-pct` (-; hand)
- `aea90364.jurisdiction.ar.frequency_hz` (-; hand)
- `aea90364.jurisdiction.ar.voltages_lv` (-; hand)
- `arch.code.gap` (-; hand)
- `datasheets.params.catalog_abb_breakers` (-; hand)
- `datasheets.params.catalog_prysmian_cables` (-; hand)
- `datasheets.params.catalog_schneider_electric_breakers` (-; hand)
- `datasheets.params.catalog_siemens_breakers` (-; hand)
- `drawing.code.formats` (-; hand)
- `drawing.code.gap` (-; hand)
- `drawing.code.standard_scales` (-; hand)
- `drawing.code.unit_mm` (-; hand)
- `dxf.code.altura_legal_mm` (-; hand)
- `dxf.code.altura_texto_mm` (-; hand)
- `dxf.code.fs_rotulo` (-; hand)
- `dxf.code.px_por_mm` (-; hand)
- `dxf.layers.lineweights` (-; hand)
- `hvac.code.air_latent_w_per_ls_kgkg` (-; hand)
- `hvac.code.air_sensible_w_per_ls_k` (-; hand)
- `hvac.code.watts_per_refrigeration_ton` (-; hand)
- `hvac.typical.params.default_infiltration_ach` (-; hand)
- `hvac.typical.params.default_lighting_use_factor` (-; hand)
- `hvac.typical.params.person_latent_w` (-; hand)
- `hvac.typical.params.person_sensible_w` (-; hand)
- `hvac.typical.params.typical_cop` (-; hand)
- `hvac.typical.solar.e` (-; hand)
- `hvac.typical.solar.h` (-; hand)
- `hvac.typical.solar.n` (-; hand)
- `hvac.typical.solar.ne` (-; hand)
- `hvac.typical.solar.nw` (-; hand)
- `hvac.typical.solar.s` (-; hand)
- `hvac.typical.solar.se` (-; hand)
- `hvac.typical.solar.sw` (-; hand)
- `hvac.typical.solar.w` (-; hand)
- `hvac.typical.ventilation.classroom` (-; hand)
- `hvac.typical.ventilation.default` (-; hand)
- `hvac.typical.ventilation.meeting_room` (-; hand)
- `hvac.typical.ventilation.office` (-; hand)
- `hvac.typical.ventilation.restaurant` (-; hand)
- `hvac.typical.ventilation.retail` (-; hand)
- `lighting.data.luminaires` (-; hand)
- `lighting.data.maintenance.interior_range` (UNAC chapter III; hand)
- `lighting.data.room_types` (-; hand)
- `lighting.params.beam_utilisation_range` (-; hand)
- `lighting.params.cavity.rcr_factor` (-; hand)
- `lighting.params.conformity.direct_factor` (-; hand)
- `lighting.params.defaults.area_beam_utilisation` (-; hand)
- `lighting.params.defaults.work_plane_height_m` (-; hand)
- `lighting.params.emergency` (EN 1838 (as recalled in code); hand)
- `lighting.params.photometry_max_output_ratio` (-; hand)
- `lighting.params.point_grid` (-; hand)
- `lighting.params.uniformity_limits` (-; hand)
- `lighting.standard.d351-79.edition` (Decreto 351/79 (Ley 19587), Cap. 12, Anexo IV; hand)
- `plan.clash.rules` (-; hand)
- `plan.knowledge.sanitaria_cloacas.pendiente_minima` (-; hand)
- `plan.params.coordination.story_height_m` (-; hand)
- `plan.params.dxf.text_height_m` (-; hand)
- `plan.params.geometry.snap_tolerance_m` (-; hand)
- `plan.params.style` (-; hand)
- `plan.typical.design.families` (-; hand)
- `plan.typical.occupancy.conduit_pct` (-; hand)
- `plan.typical.occupancy.default_cable_mm` (-; hand)
- `plan.typical.occupancy.tray_pct` (-; hand)
- `plan.typical.sizing.cable_mm_by_section` (-; hand)
- `plan.typical.sizing.conduit_mm` (-; hand)
- `plan.typical.sizing.tray_fill_max_pct` (-; hand)
- `plan.typical.tray_catalogue` (-; hand)
- `pv.typical.faiman.u0` (-; hand)
- `pv.typical.faiman.u1` (-; hand)
- `pv.typical.iam_ashrae_b0` (-; hand)
- `pv.typical.inverter.eta_nom` (-; hand)
- `pv.typical.inverter.eta_ref` (-; hand)
- `pv.typical.losses_pct.age` (-; hand)
- `pv.typical.losses_pct.availability` (-; hand)
- `pv.typical.losses_pct.connections` (-; hand)
- `pv.typical.losses_pct.lid` (-; hand)
- `pv.typical.losses_pct.mismatch` (-; hand)
- `pv.typical.losses_pct.nameplate_rating` (-; hand)
- `pv.typical.losses_pct.shading` (-; hand)
- `pv.typical.losses_pct.snow` (-; hand)
- `pv.typical.losses_pct.soiling` (-; hand)
- `pv.typical.losses_pct.wiring` (-; hand)
- `pv.typical.solar_constant_w_m2` (-; hand)
- `pv.typical.strings.isc_factor` (-; hand)
- `pv.typical.strings.policy` (-; hand)
- `receptacles.data.circuits.tue` (-; hand)
- `receptacles.data.circuits.tug` (-; hand)
- `receptacles.data.mounting.wet_min_m` (-; hand)
- `receptacles.data.receptacles` (IRAM 2071 (named in titles); hand)
- `receptacles.data.uses.classroom` (-; hand)
- `receptacles.data.uses.general` (-; hand)
- `receptacles.data.uses.workshop` (-; hand)
- `receptacles.params.corner_clearance_m` (-; hand)
- `receptacles.params.default_mount_height_m` (-; hand)
- `terminal_blocks.params.terminal_sizes` (-; hand)
- `titleblock.code.t25` (IRAM 4503; hand)
- `titleblock.layout.default_block` (IRAM 4508; hand)
- `titleblock.layout.default_pens` (IRAM 4502 / 4508; hand)
- `titleblock.layout.default_text` (-; hand)
- `transformer_sizing.params.standard_ratings` (-; hand)

## Conflictos

- `aea90364.code.aea_ampacity.default.ambiente_suelo_rho`: duplicated literals of the pipeline defaults
- `aea90364.code.aea_export.du_aviso_pct`: duplicated literal; same 5 % as aea90364.code.aea_pipeline.du_acum_max_pct
- `aea90364.code.aea_export.serie_s_mm2`: conflicts with aea90364.code.aea_pipeline.serie_s_mm2: this series has 0.5, 0.75, 400, 500, 630 mm2 not in the pipeline
- `aea90364.code.aea_feeder_report.default.tablero`: duplicated literals; the report text also hardcodes reactance 0,08 ohm/km
- `aea90364.code.aea_pipeline.c_max_bt`: duplicated literal; same value as aea90364.code.short_circuit.c_max_bt_tol_6 (1.05) and JSON /constantes/impedancias_estandar/c_fuente_max (1.05)
- `aea90364.code.aea_pipeline.default.insulation`: conflicts with aea90364.criterion.insulation: design-criteria.json default is XLPE, code fallback is PVC
- `aea90364.code.aea_pipeline.margin_motor`: duplicated literal; same 1.25 as aea90364.code.aea_demand.corriente_alimentador_motores.factor
- `aea90364.code.aea_pipeline.serie_s_mm2`: conflicts with aea90364.code.aea_export.serie_s_mm2: the export series is wider (0.5 to 630 mm2)
- `aea90364.code.board_figures.default.tablero`: duplicated literals of the pipeline defaults
- `aea90364.code.grouping.default.tablero`: duplicated literals of the pipeline defaults
- `aea90364.constant.771-13-i-secciones-minimas-mm2`: duplicated literal: aea90364.criterion.min-section-lighting-mm2 (1.5), aea90364.criterion.min-section-sockets-mm2 (2.5)
- `aea90364.constant.771-19-limites-caida-pct`: duplicated literal: aea90364.criterion.vd-sectional-pct (1), aea90364.criterion.vd-lighting-sockets-pct (3), aea90364.criterion.vd-motors-pct (5)
- `aea90364.constant.fuerza-motriz`: duplicated literal: 15 also in constantes/771.19_limites_caida_pct/motor_arranque
- `aea90364.criterion.ambient-temp-c`: duplicated literal: default also stated by aea90364.table.771-16-i
- `aea90364.criterion.min-section-lighting-mm2`: duplicated literal: default also stated by aea90364.constant.771-13-i-secciones-minimas-mm2
- `aea90364.criterion.min-section-sockets-mm2`: duplicated literal: default also stated by aea90364.constant.771-13-i-secciones-minimas-mm2
- `aea90364.criterion.soil-resistivity-kmw`: duplicated literal: default also stated by aea90364.table.771-16-v
- `aea90364.criterion.soil-temp-c`: duplicated literal: default also stated by aea90364.table.771-16-v
- `aea90364.criterion.vd-lighting-sockets-pct`: duplicated literal: default also stated by aea90364.constant.771-19-limites-caida-pct
- `aea90364.criterion.vd-motors-pct`: duplicated literal: default also stated by aea90364.constant.771-19-limites-caida-pct
- `aea90364.criterion.vd-sectional-pct`: duplicated literal: default also stated by aea90364.constant.771-19-limites-caida-pct

## Reglas indexadas automáticamente

Salen de los campos propios de cada regla (id, norma, edición, cláusula, página). No tienen registro a mano.

### AEA 90364-4-41 (2006): 8 reglas

| id | cláusula | página | verificación | revisión |
|---|---|---|---|---|
| `aea90364.rule.proteccion-choques-dd-30ma-circuitos-obligados` | 412.5.3 | p. 41-40 / PDF 60 | ocr | pending |
| `aea90364.rule.proteccion-choques-dd-30ma-proteccion-adicional` | 412.5.1 y 412.5.2 | p. 41-40 / PDF 60 | ocr | pending |
| `aea90364.rule.proteccion-choques-equipotencial-suplementaria-si-no-alcanza` | 413.1.3.5 | p. 41-49 / PDF 69 | ocr | pending |
| `aea90364.rule.proteccion-choques-tension-limite-24v` | 413.1.3 | p. 41-47 / PDF 67 | ocr | pending |
| `aea90364.rule.proteccion-choques-tiempos-tabla-41-3` | Tabla 41.3 y 413.1.3.1 | p. 41-48 / PDF 68 | visual | pending |
| `aea90364.rule.proteccion-choques-tn-s-tiempo-2s` | 413.1.3.2 | p. 41-49 / PDF 69 | ocr | pending |
| `aea90364.rule.proteccion-choques-tt-solo-diferenciales` | 413.1.3 | p. 41-47 / PDF 67 | ocr | pending |
| `aea90364.rule.proteccion-choques-tt-tiempo-1s` | 413.1.3.3 | p. 41-49 / PDF 69 | ocr | pending |

### AEA 90364-4-43 (2006): 8 reglas

| id | cláusula | página | verificación | revisión |
|---|---|---|---|---|
| `aea90364.rule.proteccion-sobrecorrientes-am-no-sobrecarga` | 432.3 Nota 1 | p. 43-9 / PDF 157 | ocr | pending |
| `aea90364.rule.proteccion-sobrecorrientes-coordinacion-ib-in-iz` | 433.1 | p. 43-10 / PDF 158 | visual | pending |
| `aea90364.rule.proteccion-sobrecorrientes-i2-definicion` | 433.1 | p. 43-10 / PDF 158 | ocr | pending |
| `aea90364.rule.proteccion-sobrecorrientes-neutro-it-no-distribuir` | 431.2.2 | p. 43-7 / PDF 155 | ocr | pending |
| `aea90364.rule.proteccion-sobrecorrientes-neutro-proteccion-igual-seccion` | 431.2.1 | p. 43-7 / PDF 155 | ocr | pending |
| `aea90364.rule.proteccion-sobrecorrientes-neutro-secuencia-maniobra` | 431.3 | p. 43-8 / PDF 156 | ocr | pending |
| `aea90364.rule.proteccion-sobrecorrientes-poder-de-corte` | 432.1 Nota 2 | p. 43-8 / PDF 156 | ocr | pending |
| `aea90364.rule.proteccion-sobrecorrientes-temperaturas-tabla-43-1` | Tabla 43.1 | p. 43-6 / PDF 154 | visual | pending |

### AEA 90364-5-51 (2006): 4 reglas

| id | cláusula | página | verificación | revisión |
|---|---|---|---|---|
| `aea90364.rule.colores-cubierta-verde-amarilla-no-activos` | 514.3.3 | p. 51-19 / PDF 45 | ocr | pending |
| `aea90364.rule.colores-lineas` | 514.3.3 | p. 51-19 / PDF 45 | visual | pending |
| `aea90364.rule.colores-neutro-pe` | 514.3.1 | p. 51-19 / PDF 45 | visual | pending |
| `aea90364.rule.colores-pen-marcado` | 514.3.2 | p. 51-19 / PDF 45 | ocr | pending |

### AEA 90364-5-52 (2006): 13 reglas

| id | cláusula | página | verificación | revisión |
|---|---|---|---|---|
| `aea90364.rule.conductores-caida-tension-iluminacion` | 525 1) | p. 52-63 / PDF 117 | ocr | pending |
| `aea90364.rule.conductores-caida-tension-motores` | 525 2) | p. 52-63 / PDF 117 | ocr | pending |
| `aea90364.rule.conductores-caida-tension-otras-cargas` | 525 3) | p. 52-63 / PDF 117 | ocr | pending |
| `aea90364.rule.conductores-caida-tension-seccionales-recomendado` | 525 Nota | p. 52-63 / PDF 117 | ocr | pending |
| `aea90364.rule.conductores-neutro-armonicas-145` | 524.2.3 | p. 52-63 / PDF 117 | ocr | pending |
| `aea90364.rule.conductores-neutro-igual-a-linea` | 524.2.1 | p. 52-62 / PDF 116 | ocr | pending |
| `aea90364.rule.conductores-neutro-no-comun` | 524.2.4 | p. 52-63 / PDF 117 | ocr | pending |
| `aea90364.rule.conductores-neutro-reducido` | 524.2.2 | p. 52-63 / PDF 117 | ocr | pending |
| `aea90364.rule.conductores-secciones-minimas-tabla-52-24` | Tabla 52.24 | p. 52-62 / PDF 116 | visual | pending |
| `aea90364.rule.curvas-canerias-distancia-entre-curvas` | 521.8.8 | p. 52-24 / PDF 78 | ocr | pending |
| `aea90364.rule.curvas-canerias-max-tres-curvas` | 521.8.8 | p. 52-24 / PDF 78 | ocr | pending |
| `aea90364.rule.curvas-canerias-radios-metalicos-tabla-52-11` | Tabla 52.11 | p. 52-24 / PDF 78 | visual | pending |
| `aea90364.rule.curvas-canerias-radios-sinteticos-tabla-52-12` | Tabla 52.12 | p. 52-24 / PDF 78 | visual | pending |

### AEA 90364-5-54 (2006): 38 reglas

| id | cláusula | página | verificación | revisión |
|---|---|---|---|---|
| `aea90364.rule.conductores-proteccion-equipotencial-principal` | 544.1.1 | p. 54-17 / PDF 257 | ocr | pending |
| `aea90364.rule.conductores-proteccion-equipotencial-suplementario-masa-extrana` | 544.2.2 | p. 54-17 / PDF 257 | ocr | pending |
| `aea90364.rule.conductores-proteccion-equipotencial-suplementario-masa-masa` | 544.2.1 | p. 54-17 / PDF 257 | ocr | pending |
| `aea90364.rule.conductores-proteccion-k-cubierta-metalica-tabla-54-9` | Tabla 54.9 | p. 54-13 / PDF 253 | visual | pending |
| `aea90364.rule.conductores-proteccion-k-desnudos-tabla-54-10` | Tabla 54.10 | p. 54-14 / PDF 254 | visual | pending |
| `aea90364.rule.conductores-proteccion-k-pe-aislado-tabla-54-6` | Tabla 54.6 | p. 54-12 / PDF 252 | visual | pending |
| `aea90364.rule.conductores-proteccion-k-pe-desnudo-tabla-54-7` | Tabla 54.7 | p. 54-13 / PDF 253 | visual | pending |
| `aea90364.rule.conductores-proteccion-k-pe-en-cable-tabla-54-8` | Tabla 54.8 | p. 54-13 / PDF 253 | visual | pending |
| `aea90364.rule.conductores-proteccion-no-usar-como-pe` | 543.2.3 | p. 54-15 / PDF 255 | ocr | pending |
| `aea90364.rule.conductores-proteccion-pe-comun-varios-circuitos` | 543.1.4 | p. 54-14 / PDF 254 | ocr | pending |
| `aea90364.rule.conductores-proteccion-pe-formula-adiabatica` | 543.1.2 | p. 54-12 / PDF 252 | ocr | pending |
| `aea90364.rule.conductores-proteccion-pe-junto-a-activos-con-sobreintensidad` | 543.6 | p. 54-16 / PDF 256 | ocr | pending |
| `aea90364.rule.conductores-proteccion-pe-minimo-independiente` | 543.1.3 | p. 54-14 / PDF 254 | ocr | pending |
| `aea90364.rule.conductores-proteccion-pe-reforzado-fuga-10ma` | 543.7 | p. 54-16 / PDF 256 | ocr | pending |
| `aea90364.rule.conductores-proteccion-pe-seccion-normalizada-superior` | 543.1.2 | p. 54-12 / PDF 252 | ocr | pending |
| `aea90364.rule.conductores-proteccion-pe-sin-dispositivo-de-corte` | 543.3.3 | p. 54-15 / PDF 255 | ocr | pending |
| `aea90364.rule.conductores-proteccion-pe-sin-guirnalda` | 543.3.5 | p. 54-15 / PDF 255 | ocr | pending |
| `aea90364.rule.conductores-proteccion-pe-tabla-54-5` | Tabla 54.5 | p. 54-11 / PDF 251 | visual | pending |
| `aea90364.rule.conductores-proteccion-pe-tipos-permitidos` | 543.2.1 | p. 54-14 / PDF 254 | ocr | pending |
| `aea90364.rule.conductores-proteccion-pen-prohibido-en-inmuebles` | 543.4 Nota 1 | p. 54-15 / PDF 255 | ocr | pending |
| `aea90364.rule.conductores-proteccion-pen-seccion-minima` | 543.4.1 | p. 54-16 / PDF 256 | ocr | pending |
| `aea90364.rule.conductores-proteccion-pen-separacion-n-pe` | 543.4.3 | p. 54-16 / PDF 256 | ocr | pending |
| `aea90364.rule.puesta-a-tierra-anillo-cimientos-dos-hincados` | 542.2.3 | p. 54-8 / PDF 248 | ocr | pending |
| `aea90364.rule.puesta-a-tierra-armaduras-no-electrodo` | 542.2.3 | p. 54-8 / PDF 248 | ocr | pending |
| `aea90364.rule.puesta-a-tierra-barra-medicion-dimensiones` | 542.4 | p. 54-9 / PDF 249 | ocr | pending |
| `aea90364.rule.puesta-a-tierra-bep-desconexion-individual` | 542.4.2 | p. 54-10 / PDF 250 | ocr | pending |
| `aea90364.rule.puesta-a-tierra-bep-obligatoria` | 542.4.1 | p. 54-9 / PDF 249 | ocr | pending |
| `aea90364.rule.puesta-a-tierra-canerias-no-electrodo` | 542.2.6 | p. 54-8 / PDF 248 | ocr | pending |
| `aea90364.rule.puesta-a-tierra-conductor-enterrado-tabla-54-3` | Tabla 54.3 | p. 54-9 / PDF 249 | visual | pending |
| `aea90364.rule.puesta-a-tierra-conductor-fe-color` | 542.4.1 Nota 2 | p. 54-10 / PDF 250 | ocr | pending |
| `aea90364.rule.puesta-a-tierra-electrodo-camara-inspeccion` | 542.2.6 Nota 2 | p. 54-8 / PDF 248 | ocr | pending |
| `aea90364.rule.puesta-a-tierra-electrodos-dimensiones-tabla-54-2` | Tabla 54.2 | p. 54-6 / PDF 246 | visual | pending |
| `aea90364.rule.puesta-a-tierra-electrodos-materiales-resistencia` | 542.2.1 | p. 54-5 / PDF 245 | ocr | pending |
| `aea90364.rule.puesta-a-tierra-jabalina-minima` | 542.2.3 | p. 54-8 / PDF 248 | ocr | pending |
| `aea90364.rule.puesta-a-tierra-jabalinas-separacion` | 542.2.2 Nota | p. 54-7 / PDF 247 | ocr | pending |
| `aea90364.rule.puesta-a-tierra-tt-ra-maxima` | 541.3 | p. 54-4 / PDF 244 | ocr | pending |
| `aea90364.rule.puesta-a-tierra-tt-ra-tabla-54-1` | Tabla 54.1 | p. 54-5 / PDF 245 | visual | pending |
| `aea90364.rule.puesta-a-tierra-verificar-por-medicion` | 542.2.2 | p. 54-7 / PDF 247 | ocr | pending |

### AEA 90364-7-701 (2012): 12 reglas

| id | cláusula | página | verificación | revisión |
|---|---|---|---|---|
| `aea90364.rule.banos-diferencial-30ma` | 701.412.5 | p. 8 | text | pending |
| `aea90364.rule.banos-ip-zona-0` | 701.512.2 | p. 10 | text | pending |
| `aea90364.rule.banos-ip-zona-1` | 701.512.2 | p. 10 | text | pending |
| `aea90364.rule.banos-ip-zona-2` | 701.512.2 | p. 10 | text | pending |
| `aea90364.rule.banos-ip-zona-3` | 701.512.2 | p. 10 | text | pending |
| `aea90364.rule.banos-separacion-electrica` | 701.413.5 | p. 10 | text | pending |
| `aea90364.rule.banos-zona0-ducha-sin-receptaculo` | 701.30.2 | p. 6 | text | pending |
| `aea90364.rule.banos-zona1-altura` | 701.30.3 | p. 7 | text | pending |
| `aea90364.rule.banos-zona1-ducha-sin-receptaculo-fija` | 701.30.3 | p. 7 | text | pending |
| `aea90364.rule.banos-zona1-duchador-movil` | 701.30.3 | p. 7 | text | pending |
| `aea90364.rule.banos-zona2-ancho` | 701.30.4 | p. 7 | text | pending |
| `aea90364.rule.tableros-no-en-ba-os-701` | 701.512.4 | p. 12 | text | pending |

### AEA 90364-7-722 (2018): 6 reglas

| id | cláusula | página | verificación | revisión |
|---|---|---|---|---|
| `aea90364.rule.tomacorrientes-ev-diferencial-30ma-clase-a` | 722, apartado 3.2 | p. 12 | text | pending |
| `aea90364.rule.tomacorrientes-ev-ip-intemperie` | 722, apartado 3.5.1 y 3.5.2 | p. 13 | text | pending |
| `aea90364.rule.tomacorrientes-ev-modo-0-2-interior` | 722, apartado 3.4.1 | p. 13 | text | pending |
| `aea90364.rule.tomacorrientes-ev-modo-3-4-acu` | 722, apartado 3.4.2 y 3.5.2 | p. 13 | text | pending |
| `aea90364.rule.tomacorrientes-ev-un-vehiculo-por-modulo` | 722, apartado 3.1 | p. 12 | text | pending |
| `aea90364.rule.tomacorrientes-ev-una-acometida` | 722, apartado 3.6 | p. 13 | text | pending |

### AEA 90364-7-770 (2017): 6 reglas

| id | cláusula | página | verificación | revisión |
|---|---|---|---|---|
| `aea90364.rule.canalizaciones-recomendacion-r25-viviendas` | 770.7.1 | p. 13 | text | pending |
| `aea90364.rule.otros-cercas-electrificadas-altura` | 770.7.7 | p. 17 | text | pending |
| `aea90364.rule.tableros-reserva-770` | 770.16.4 | p. 53 | text | pending |
| `aea90364.rule.tomacorrientes-altura-arista-inferior-770` | 770.7.2 | p. 13 | text | pending |
| `aea90364.rule.tomacorrientes-baldeado-770` | 770.7.2 | p. 13 | text | pending |
| `aea90364.rule.tomacorrientes-mesadas-770` | 770.7.2 | p. 13 | text | pending |

### AEA 90364-7-771 (2006): 82 reglas

| id | cláusula | página | verificación | revisión |
|---|---|---|---|---|
| `aea90364.rule.bandejas-altura-montaje` | 771.12.3.9.3 | p. 69 | text | pending |
| `aea90364.rule.bandejas-reserva-20pct` | 771.12.3.9.2 | p. 67 | text | pending |
| `aea90364.rule.bandejas-separacion-entre-bandejas` | 771.12.3.9.2 | p. 67 | text | pending |
| `aea90364.rule.bandejas-solo-control-40pct` | 771.12.3.9.2 | p. 67 | text | pending |
| `aea90364.rule.bandejas-tapas-hasta-2-2m` | 771.12.3.9.3 | p. 69 | text | pending |
| `aea90364.rule.bandejas-una-capa` | 771.12.3.9.2 | p. 67 | text | pending |
| `aea90364.rule.banos-hidromasaje-alimentacion` | 771.8.5 s) | p. 43 | text | pending |
| `aea90364.rule.canalizaciones-cajas-de-paso-distancia` | 771.12.3.8.3 | p. 63 | text | pending |
| `aea90364.rule.canalizaciones-columnas-luminarias-35pct` | 771-B.8.3.7 | p. 182 | text | pending |
| `aea90364.rule.canalizaciones-curvas-fabrica-tabla` | Tabla 771.12.VIII | p. 64 | text | pending |
| `aea90364.rule.canalizaciones-curvas-max-entre-cajas` | 771.12.3.1 | p. 54 | text | pending |
| `aea90364.rule.canalizaciones-diametro-min-principal-seccional` | 771.12.3.13.4 | p. 83 | text | pending |
| `aea90364.rule.canalizaciones-diametro-min-terminales` | 771.12.3.13.4 | p. 83 | text | pending |
| `aea90364.rule.canalizaciones-distancia-cajas-a-marcos-solados-techos` | 771.12.3.1 | p. 54 | text | pending |
| `aea90364.rule.canalizaciones-distancia-entre-curvas` | 771.12.3.8.5 | p. 64 | text | pending |
| `aea90364.rule.canalizaciones-llenado-max-ca-os-no-tabulados` | 771.12.3.13.4 | p. 83 | text | pending |
| `aea90364.rule.canalizaciones-ortogonalidad` | 771.12.3.1 | p. 54 | text | pending |
| `aea90364.rule.canalizaciones-perfiles-ocupacion` | 771.12.3.10.2 | p. 71 | text | pending |
| `aea90364.rule.canalizaciones-sujecion-flexibles` | 771.12.3.3.4 b) | p. 58 | text | pending |
| `aea90364.rule.canalizaciones-tablero-principal-a-seccional` | 771.8.5 t) | p. 43 | text | pending |
| `aea90364.rule.canalizaciones-un-conductor-en-ca-o-metalico` | 771.12.3.13.4 | p. 83 | text | pending |
| `aea90364.rule.canalizaciones-un-conductor-en-ca-o-no-metalico` | 771.12.3.13.4 | p. 83 | text | pending |
| `aea90364.rule.circuitos-apm` | 771.7.6 c2) I | p. 24 | text | pending |
| `aea90364.rule.circuitos-ate-bocas-max` | 771.7.6 c1) II | p. 24 | text | pending |
| `aea90364.rule.circuitos-caja-de-paso-como-boca` | 771.7.6 Nota 1 | p. 21 | text | pending |
| `aea90364.rule.circuitos-equilibrio-trifasico` | 771.8.5 q) | p. 43 | text | pending |
| `aea90364.rule.circuitos-fuentes-comunicaciones-2200va` | 771.8.5 j) | p. 42 | text | pending |
| `aea90364.rule.circuitos-iluminacion-mayor-10a` | 771.8.5 b) | p. 42 | text | pending |
| `aea90364.rule.circuitos-ite` | 771.7.6 c2) IV | p. 25 | text | pending |
| `aea90364.rule.circuitos-iue-a-la-intemperie` | 771.7.6 b) I | p. 23 | text | pending |
| `aea90364.rule.circuitos-iug-bocas-max` | 771.7.6 a) I | p. 22 | text | pending |
| `aea90364.rule.circuitos-iug-corriente-unitaria` | 771.7.6 a) I | p. 22 | text | pending |
| `aea90364.rule.circuitos-iug-proteccion-max` | 771.7.6 a) I | p. 22 | text | pending |
| `aea90364.rule.circuitos-mbtf` | 771.7.6 c2) III | p. 24 | text | pending |
| `aea90364.rule.circuitos-tomas-por-boca` | 771.8.5 a) | p. 42 | text | pending |
| `aea90364.rule.circuitos-tue-corriente-unitaria` | 771.7.6 b) II | p. 23 | text | pending |
| `aea90364.rule.circuitos-tug-bocas-max` | 771.7.6 a) II | p. 22 | text | pending |
| `aea90364.rule.circuitos-tug-corriente-unitaria` | 771.7.6 a) II | p. 22 | text | pending |
| `aea90364.rule.circuitos-tug-proteccion-max` | 771.7.6 a) II | p. 22 | text | pending |
| `aea90364.rule.circuitos-uso-especial-proteccion-y-bocas` | 771.7.6 b) | p. 23 | text | pending |
| `aea90364.rule.enterrados-bajo-construcciones` | 771.12.4.2.3 | p. 87 | text | pending |
| `aea90364.rule.enterrados-cruces-ca-o-de-reserva` | 771.12.4.2.3 | p. 87 | text | pending |
| `aea90364.rule.enterrados-diametro-conductos-tabla` | Tabla 771.12.XIV | p. 86 | text | pending |
| `aea90364.rule.enterrados-pendiente-conductos` | 771.12.4.2.2 | p. 86 | text | pending |
| `aea90364.rule.enterrados-profundidad-cables-directos` | 771.12.4.2.1 | p. 86 | text | pending |
| `aea90364.rule.enterrados-proteccion-hormigon-pobre` | 771.12.4.2.2 | p. 86 | text | pending |
| `aea90364.rule.enterrados-recubrimiento-conductos` | 771.12.4.2.2 | p. 86 | text | pending |
| `aea90364.rule.iluminacion-deposito-densidad-elevado` | 771.8.3.3.3.3 | p. 37 | text | pending |
| `aea90364.rule.iluminacion-deposito-densidad-medio` | 771.8.3.3.3.2 | p. 36 | text | pending |
| `aea90364.rule.iluminacion-deposito-densidad-minimo` | 771.8.3.3.3.1 | p. 36 | text | pending |
| `aea90364.rule.iluminacion-deposito-densidad-superior` | 771.8.3.3.3.4 | p. 37 | text | pending |
| `aea90364.rule.iluminacion-escaleras-una-boca-cada-5m` | 771.8.5 g) | p. 42 | text | pending |
| `aea90364.rule.iluminacion-escuelas-louver` | 771.8.4 i) | p. 41 | text | pending |
| `aea90364.rule.iluminacion-luminarias-puertas-acceso-2-5m` | 771-B.8.2.1 | p. 177 | text | pending |
| `aea90364.rule.iluminacion-mbts-comando-ambientes-mojados` | 771.8.5 l) | p. 43 | text | pending |
| `aea90364.rule.iluminacion-ventiladores-cuentan-como-boca` | 771.8.5 c) | p. 42 | text | pending |
| `aea90364.rule.interruptores-altura-centro` | 771.8.6.1 | p. 44 | text | pending |
| `aea90364.rule.interruptores-ascensores` | 771.8.6.1 | p. 44 | text | pending |
| `aea90364.rule.interruptores-distancia-al-marco` | 771.8.6.1 | p. 44 | text | pending |
| `aea90364.rule.interruptores-garajes-altura-minima` | 771.8.3.4 | p. 37 | text | pending |
| `aea90364.rule.interruptores-no-compartir-caja-con-tomas-bajos` | 771.8.5 p) | p. 43 | text | pending |
| `aea90364.rule.interruptores-pasillos-mayores-3m` | 771.8.6.1 | p. 44 | text | pending |
| `aea90364.rule.tableros-altura-borneras` | 771.20.4 | p. 147 | text | pending |
| `aea90364.rule.tableros-altura-comandos` | 771.20.4 | p. 147 | text | pending |
| `aea90364.rule.tableros-gabinetes-en-zonas-de-vehiculos` | 771.20.4 | p. 147 | text | pending |
| `aea90364.rule.tableros-ip-intemperie-principal` | 771.20.3.1 | p. 147 | text | pending |
| `aea90364.rule.tableros-ip-minimo-viviendas-oficinas` | 771.20.4 | p. 147 | text | pending |
| `aea90364.rule.tableros-montaje-componentes` | 771.20.4 | p. 147 | text | pending |
| `aea90364.rule.tableros-no-en-ba-os` | 771.20.3.1 y 771.20.3.2 | p. 147 | text | pending |
| `aea90364.rule.tableros-reserva-771` | 771.20.4 | p. 147 | text | pending |
| `aea90364.rule.tableros-verificacion-calentamiento` | 771.20.4 | p. 147 | text | pending |
| `aea90364.rule.tomacorrientes-altura-arista-inferior-771` | 771.8.6.2 | p. 44 | text | pending |
| `aea90364.rule.tomacorrientes-ate-color-rojo` | 771.7.6 c1) II | p. 24 | text | pending |
| `aea90364.rule.tomacorrientes-baldeado-771` | 771.8.6.2 | p. 44 | text | pending |
| `aea90364.rule.tomacorrientes-deposito-perimetro` | 771.8.3.3.3.1 a 771.8.3.3.3.4 | p. 36 | text | pending |
| `aea90364.rule.tomacorrientes-escuelas-aulas-pizarron` | 771.8.4 j) | p. 41 | text | pending |
| `aea90364.rule.tomacorrientes-escuelas-inicial-1-7m` | 771.8.4 j) | p. 41 | text | pending |
| `aea90364.rule.tomacorrientes-mesadas-771` | 771.8.6.2 | p. 44 | text | pending |
| `aea90364.rule.tomacorrientes-mixtas-bajo-090` | 771.8.5 p) | p. 43 | text | pending |
| `aea90364.rule.tomacorrientes-ninos-bajos-2x10t-771` | 771.8.6.2 | p. 44 | text | pending |
| `aea90364.rule.tomacorrientes-orificios-hacia-arriba` | 771.8.6.2 | p. 44 | text | pending |
| `aea90364.rule.tomacorrientes-toilette-toma-en-iluminacion` | 771.8.5 n) | p. 43 | text | pending |

### D351-79 (-): 23 reglas

| id | cláusula | página | verificación | revisión |
|---|---|---|---|---|
| `lighting.rule.d351-aiv-t2-banco-cajas` | Anexo IV, Tabla 2, Bancos | - | unverified | pending |
| `lighting.rule.d351-aiv-t2-banco-general` | Anexo IV, Tabla 2, Bancos | - | unverified | pending |
| `lighting.rule.d351-aiv-t2-garaje-general` | Anexo IV, Tabla 2, Garajes | - | unverified | pending |
| `lighting.rule.d351-aiv-t2-hotel-circulacion` | Anexo IV, Tabla 2, Hoteles | - | unverified | pending |
| `lighting.rule.d351-aiv-t2-hotel-hall` | Anexo IV, Tabla 2, Hoteles | - | unverified | pending |
| `lighting.rule.d351-aiv-t2-industria-otros` | Anexo IV, Tabla 2 | - | unverified | pending |
| `lighting.rule.d351-aiv-t2-mecanica-banco-general` | Anexo IV, Tabla 2, Mecanica general | - | unverified | pending |
| `lighting.rule.d351-aiv-t2-mecanica-deposito` | Anexo IV, Tabla 2, Mecanica general | - | unverified | pending |
| `lighting.rule.d351-aiv-t2-oficina-circulacion` | Anexo IV, Tabla 2, Oficinas | - | unverified | pending |
| `lighting.rule.d351-aiv-t2-oficina-conferencias` | Anexo IV, Tabla 2, Oficinas | - | unverified | pending |
| `lighting.rule.d351-aiv-t2-oficina-especial` | Anexo IV, Tabla 2, Oficinas | - | unverified | pending |
| `lighting.rule.d351-aiv-t2-oficina-general` | Anexo IV, Tabla 2, Oficinas | - | unverified | pending |
| `lighting.rule.d351-aiv-t2-oficina-hall` | Anexo IV, Tabla 2, Oficinas | - | unverified | pending |
| `lighting.rule.d351-aiv-t2-vivienda-bano` | Anexo IV, Tabla 2, Vivienda | - | unverified | pending |
| `lighting.rule.d351-aiv-t2-vivienda-cocina` | Anexo IV, Tabla 2, Vivienda | - | unverified | pending |
| `lighting.rule.d351-aiv-t2-vivienda-dormitorio` | Anexo IV, Tabla 2, Vivienda | - | unverified | pending |
| `lighting.rule.d351-aiv-t3-central` | Anexo IV, Tabla 3 | - | unverified | pending |
| `lighting.rule.d351-aiv-t3-dos-puntos` | Anexo IV, Tabla 3 | - | unverified | pending |
| `lighting.rule.d351-aiv-t3-fuente-fondo` | Anexo IV, Tabla 3 | - | unverified | pending |
| `lighting.rule.d351-aiv-t3-periferico` | Anexo IV, Tabla 3 | - | unverified | pending |
| `lighting.rule.d351-aiv-t4` | Anexo IV, Tabla 4 | - | unverified | pending |
| `lighting.rule.d351-aiv-uniformidad` | Anexo IV, 1 (iluminacion general) | - | unverified | pending |
| `lighting.rule.d351-art76-emergencia` | Art. 76 | - | unverified | pending |
