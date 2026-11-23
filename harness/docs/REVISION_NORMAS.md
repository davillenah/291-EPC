# Valores de normas que el dueño tiene que revisar

Generado por `python harness/tools/build/review_list.py`; no se edita a mano. Un valor **sin revisar** se usa para calcular pero el resultado lo avisa; solo el dueño lo aprueba.

## 1. En la página de normas

Se revisan en la pantalla de normas (aprobar, corregir o rechazar cada punto). Pendientes: **341**. Orden: primero lo que más motores arrastra si cambia (columna *Motores afectados*, de `DEPENDENCIAS.md`), así se aprueba antes lo que más destraba.

| Unidad | Puntos | Pendientes | Motores afectados |
|---|---:|---:|---:|
| Tablas y constantes de cálculo (AEA 90364-7-771, 2006) | 93 | 93 | 15 |
| AEA 90364-7-771 (2006) | 82 | 82 | 15 |
| AEA 90364-5-54 (2006) | 38 | 38 | 15 |
| AEA 90364-5-52 (2006) | 13 | 13 | 15 |
| AEA 90364-7-701 (2012) | 12 | 12 | 15 |
| AEA 90364-4-41 (2006) | 8 | 8 | 15 |
| AEA 90364-4-43 (2006) | 8 | 8 | 15 |
| AEA 90364-7-722 (2018) | 6 | 6 | 15 |
| AEA 90364-7-770 (2017) | 6 | 6 | 15 |
| AEA 90364-5-51 (2006) | 4 | 4 | 15 |
| Cables, canalizaciones y diseño automático · valores típicos (a confirmar) | 7 | 7 | 7 |
| D351-79 · iluminación (valores por revisar) | 23 | 23 | 1 |
| Climatización · valores típicos (a confirmar) | 20 | 20 | 1 |
| Tomacorrientes · valores típicos (a confirmar) | 18 | 18 | 1 |
| Criterios de diseño · valores base (AR, eléctrica) | 18 | 3 | 1 |

## 2. Marcas `[VERIFICAR]` en el código de los motores

Cada una es una fórmula, un valor o una cláusula que hay que contrastar con la norma. Total: **65** en 28 archivos.

### `harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_backup.py` (1)

- línea 32: - ISO 8528 (grupos electrógenos), IEC 62040 (UPS), AEA 90364-5-56 (servicios de seguridad).  [VERIFICAR]

### `harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_catalog.py` (1)

- línea 18: Ver el campo `norma` de cada módulo.  [VERIFICAR]

### `harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_lightning.py` (1)

- línea 29: IEC 62305-2 (riesgo), IEC 62305-3 (captores y bajadas), IRAM 2184.  [VERIFICAR]

### `harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_motor.py` (1)

- línea 29: AEA 90364-7-771 (caída de tensión), AEA 90364-5-55 (motores).  [VERIFICAR]

### `harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_panel_thermal.py` (1)

- línea 27: AEA 90364-7-770 Anexo B; AEA 90364-7-771 §20.4.2 / Anexo H.3.  [VERIFICAR]

### `harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_pipeline.py` (1)

- línea 49: AEA 90364-7-771 (2006) §13, §16, §19.7; AEA 90364-7-770 (2017).  [VERIFICAR]

### `harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_reactive.py` (1)

- línea 28: - IEC 60831 / IEC 60364-5-55 (condensadores: corriente permanente de hasta 1,3 · I_n por armónicos y 1,1 de tolerancia).  [VERIFICAR]

### `harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_rules.py` (1)

- línea 25: AEA 90364-7-771 (Ed. 2006), 7-770, 7-701 (Ed. 2012), 7-722 (Ed. 2018); AEA 90364-4 y -5 (Ed. 2006).  [VERIFICAR]

### `harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_special_locations.py` (1)

- línea 25: AEA 90364-7-701 (2012); AEA 90364-7-722 (2018).  [VERIFICAR]

### `harness/src/engines/calculation/aea90364/src/epc_aea90364/board_feeders.py` (1)

- línea 10: AEA 90364-7-771 (los mismos criterios que los circuitos del tablero).  [VERIFICAR]

### `harness/src/engines/calculation/aea90364/src/epc_aea90364/board_memo.py` (1)

- línea 27: AEA 90364-4-41, 4-43, 7-771 ; IEC 60898-1, IEC 60947-2, IEC 60364-5-53 ; AEA 90909-1.  [VERIFICAR]

### `harness/src/engines/calculation/aea90364/src/epc_aea90364/hazen_williams.py` (10)

- línea 12: La constante 6,05·10⁵ es la forma habitual (Q en L/min, d en mm, p en bar/m). [VERIFICAR]
- línea 17: ρ = 1000 kg/m³ (agua) ; g = 9,80665 m/s² [VERIFICAR] ; L_eq [m] longitud equivalente
- línea 22: h_f/L = 10,67 · Q^1,852 / (C^1,852 · d^4,8704)   [m de columna de agua por m]  [VERIFICAR]
- línea 41: diámetros pequeños (< 50 mm aprox.) la exactitud decrece. [VERIFICAR]
- línea 47: NFPA 13 (rociadores) [VERIFICAR] — sin cláusulas. La forma y constante provienen de memoria.
- línea 56: : Constante de Hazen-Williams (Q [L/min], d [mm] -> bar/m). [VERIFICAR]
- línea 57: CONSTANTE_HW = 6.05e5   # [VERIFICAR]
- línea 58: EXP_Q = 1.85            # [VERIFICAR]
- línea 59: EXP_D = 4.87            # [VERIFICAR]
- línea 61: G = 9.80665             # m/s²  [VERIFICAR]

### `harness/src/engines/calculation/aea90364/src/epc_aea90364/hvac_airflow.py` (4)

- línea 19: ρ = 1,2 kg/m³ ;  cp = 1,006 kJ/(kg·K)       [VERIFICAR]
- línea 37: para caudales de ventilación. [VERIFICAR] — sin cláusulas; ningún valor normativo está embebido.
- línea 45: RHO_AIRE = 1.2    # kg/m³  [VERIFICAR]
- línea 46: CP_AIRE = 1.006   # kJ/(kg·K)  [VERIFICAR]

### `harness/src/engines/calculation/calc_common/src/epc_calc_common/aea_tables.py` (1)

- línea 24: AEA 90364-7-771 Ed. 2006, §16 (tablas 771.16.I a XI).  [VERIFICAR]

### `harness/src/engines/calculation/load_balance/src/epc_load_balance/aea_demand.py` (1)

- línea 37: AEA 90364-7-771 (2006) §8 (grados), §9 (DPMS), §13; AEA 90364-7-770 (2017) §7 (grados), §8 (DPMS); IEC 60364-5-52 (paralelo).  [VERIFICAR]

### `harness/src/engines/calculation/load_balance/src/epc_load_balance/current_and_loads.py` (1)

- línea 46: factores de simultaneidad y utilización corresponde a la guía de proyecto. [VERIFICAR]

### `harness/src/engines/calculation/voltage_drop/src/epc_voltage_drop/aea_voltage_drop.py` (1)

- línea 34: AEA 90364-7-771 §19.7 (Tabla 771.19.IV); AEA 90364-7-770 §15.6.  [VERIFICAR]

### `harness/src/engines/calculation/voltage_drop/src/epc_voltage_drop/voltage_drop.py` (1)

- línea 41: y la reglamentación local de instalaciones eléctricas aplicable. [VERIFICAR]

### `harness/src/engines/calculation/feeder_sizing/src/epc_feeder_sizing/aea_ampacity.py` (2)

- línea 21: - Aluminio solo desde 16 mm² (AEA 771.13) y con R20 de IEC 60228 clase 2 [VERIFICAR].
- línea 27: AEA 90364-7-771 §16 (771.16.I a VII), §13; IEC 60228.  [VERIFICAR]

### `harness/src/engines/calculation/feeder_sizing/src/epc_feeder_sizing/aea_conductors.py` (2)

- línea 31: AEA 90364-7-771 §13, §16, §19, Anexo H; AEA 90364-7-770 §11.  [VERIFICAR]
- línea 48: ALFA_CU            coeficiente de temperatura del cobre [1/°C]         X_CABLE_OHM_KM  reactancia típica de cable en cañería [Ω/km]  [VERIFICAR]

### `harness/src/engines/calculation/feeder_sizing/src/epc_feeder_sizing/aea_route.py` (3)

- línea 28: hace acá [VERIFICAR].
- línea 34: AEA 90364-7-771 §16 (771.16.I a VII) ; IEC 60364-5-52.  [VERIFICAR]
- línea 143: out.append(f"tramo {i}: profundidad {d:g} m mayor que la de las tablas ({ref} m): verificar el factor [VERIFICAR]")

### `harness/src/engines/calculation/feeder_sizing/src/epc_feeder_sizing/cable_thermal.py` (5)

- línea 18: Cu/PVC = 115 ; Cu/XLPE = 143 ; Al/PVC = 76 ; Al/XLPE = 94      [VERIFICAR]
- línea 25: (típicamente hasta unos 5 s). [VERIFICAR]
- línea 42: [VERIFICAR] — sin citar cláusulas.
- línea 43: - IEC 60949 (cálculo de corrientes de cortocircuito admisibles térmicamente). [VERIFICAR]
- línea 91: adv.append(f"t = {t_s} s > {_g('T_ADIABATICO_MAX_S')} s: el supuesto adiabático puede no ser válido [VERIFICAR].")

### `harness/src/engines/calculation/feeder_sizing/src/epc_feeder_sizing/conductor_selection.py` (2)

- línea 45: local. [VERIFICAR]
- línea 137: "estado_validacion": "[VERIFICAR] — BORRADOR; válido solo con tabla de norma validada"}

### `harness/src/engines/calculation/short_circuit/src/epc_short_circuit/aea_icc_decay.py` (1)

- línea 37: AEA IT 90909-1 (2005) §2.4–2.8; AEA 90909-0.  [VERIFICAR]

### `harness/src/engines/calculation/short_circuit/src/epc_short_circuit/aea_icc_factors.py` (1)

- línea 38: AEA IT 90909-1 (2005); AEA 90909-0 (IEC 60909-0).  [VERIFICAR]

### `harness/src/engines/calculation/short_circuit/src/epc_short_circuit/short_circuit.py` (16)

- línea 15: X/R por defecto 10 (R_Q = 0,1·X_Q). [VERIFICAR]
- línea 25: c_max = 1,05 si la tolerancia de tensión es 6 %;  c_max = 1,10 si es 10 %.  [VERIFICAR]
- línea 29: K_T = 0,95 · c / (1 + 0,6 · x_T) ,  x_T = X_T / Z_nominal_T (en p.u.)  [VERIFICAR]
- línea 33: con suma aritmética (conservadora) con la corriente de la red. I_LR/I_rM típico 5 a 7 [VERIFICAR].
- línea 35: κ = 1,02 + 0,98 · exp(−3 · R/X) ;  i_p = κ · √2 · Ik''   [VERIFICAR]
- línea 50: - No calcula Ik mínima (c_min = 0,95 [VERIFICAR] y R a temperatura final no están incluidos),
- línea 55: - IEC 60909-0 (corrientes de cortocircuito en redes trifásicas de c.a.). [VERIFICAR] los
- línea 67: y se renuevan con `aea_tables.limpiar_cache_tablas()`. Todos [VERIFICAR]. Forma de cada uno:
- línea 166: """K_T = 0,95·c/(1 + 0,6·x_T), x_T = X_T/Z_nominal en p.u. [VERIFICAR]."""
- línea 210: adv.append(f"Se aplicó K_T = {kt:.4f} al transformador [VERIFICAR].")
- línea 227: máxima: c_max (6 %) y R del cobre a 20 °C; mínima: c_min y R a TEMP_MIN_C. Devuelve {ik_a, ip_a, r_ohm, x_ohm, c}. [VERIFICAR]"""
- línea 240: R del cobre a 20 °C (valor máximo de Ik) y X típica del cable; una sección que no esté tabulada da ValueError. El aluminio da una Ik menor: usar cobre
- línea 246: """Aporte inicial [A] de un motor asíncrono: Ik''_M = c·(I_LR/I_rM)·I_rM. [VERIFICAR]
- línea 256: """True si el aporte de motores ≤ 5 % de Ik'' sin motores. [VERIFICAR] umbral."""
- línea 263: """κ = 1,02 + 0,98·exp(−3·R/X). [VERIFICAR]"""
- línea 275: """i_p [A] = κ·√2·Ik''. [VERIFICAR]"""

### `harness/src/engines/calculation/grounding/src/epc_grounding/aea_earthing.py` (2)

- línea 27: AEA 90364-7-771 §3, §18, Anexo C.10 y C.II.  [VERIFICAR]
- línea 196: """R de una malla de tierra [Ω] (fórmula de Sverak, IEEE 80): ρ·[1/L + 1/√(20·A)·(1 + 1/(1 + h·√(20/A)))], con L el largo total de conductor enterrado

### `harness/src/engines/calculation/selectivity/src/epc_selectivity/aea_protection.py` (1)

- línea 25: AEA 90364-4-41 (§41.3), 90364-4-43, 90364-7-771.18 y IT 90909-1.  [VERIFICAR]
