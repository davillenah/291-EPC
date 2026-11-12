# Casos de referencia independientes del motor de cálculo (AEA 90364)

Generado por `python harness/tools/build/reference_cases.py --report`. Este documento **informa**; no es una compuerta y no cambia el motor.

Cada caso recalcula el valor esperado de forma independiente: (a) fórmula cerrada con entradas declaradas, (b) un valor que los propios datos del repo declaran (se cita el puntero JSON) o (c) sin valor esperado cuando solo el texto oficial, o una decisión del dueño, puede resolverlo. No se cita ninguna norma de memoria.

## Resumen

| Estado | Casos |
|---|---|
| COINCIDE | 37 |
| DIFIERE | 7 |
| SIN VALOR OFICIAL | 7 |
| NO CORRIÓ | 4 |
| **Total** | **55** |

### Casos que difieren

| Caso | Gravedad si falla | Esperado | Motor | Diferencia |
|---|---|---|---|---|
| `b_vd_tabla_vs_formula_1_5mm2` | menor | 23.2602 V/(A.km) | 26 | +11.779 % |
| `b_vd_tabla_vs_formula_2_5mm2` | menor | 14.2817 V/(A.km) | 15 | +5.029 % |
| `m_jabalina_continuidad_L_d_100` | menor | 0.058736 % (puntos) | 33.3333 | +33.275 pp |
| `m_jabalina_continuidad_L_d_600` | menor | 0.270221 % (puntos) | 20 | +19.730 pp |
| `m_jabalina_simplificada_d10mm` | menor | 35.9861 ohm | 33.3333 | -7.372 % |
| `m_jabalina_simplificada_d30mm` | menor | 30.1578 ohm | 25 | -17.103 % |
| `t1_aislacion_por_defecto` | importante | xlpe  | pvc | - |

### Casos sin valor oficial (decisión del dueño o texto de la norma)

| Caso | Gravedad | Motor hoy |
|---|---|---|
| `k1_tiempos_desconexion_duplicado` | seguridad | 0 |
| `l4_tn_limite_zs_inconsistente` | importante | 1.36563 |
| `p2_pipeline_no_evalua_i2` | menor | False |
| `q1_corriente_cabecera_tablero` | importante | 60 |
| `r4_tomas_pasillo` | menor | 2 |
| `s2_pe_95mm2` | menor | 50 |
| `t2_aislacion_efecto_seccion` | menor | None |

### Casos que no corrieron

- `h1_agrupamiento_aire_entre_conteos`: el motor falló: MissingNormDataError: agrupamiento de 10 circuitos fuera de la Tabla 771.16.IV (ítem 1): la tabla trae solo [2, 3, 4, 5, 6, 7, 8, 9, 12, 16, 20] circuitos; no se interpola ni se repite el último factor. Indique en AGRUP_CIRCUITOS uno de esos números (reagrupe los circuitos o separe las canalizaciones)
- `h2_agrupamiento_enterrado_7`: el motor falló: MissingNormDataError: falta la separación entre cables (SEPARACION_CABLES) de la Tabla 771.16.VII.c: indique una de ['en contacto', '1 diámetro', '0,125 m', '0,25 m', '0,5 m']; no hay columna por defecto
- `h3_agrupamiento_aire_25`: el motor falló: MissingNormDataError: agrupamiento de 25 circuitos fuera de la Tabla 771.16.IV (ítem 1): la tabla trae solo [2, 3, 4, 5, 6, 7, 8, 9, 12, 16, 20] circuitos; no se interpola ni se repite el último factor. Indique en AGRUP_CIRCUITOS uno de esos números (reagrupe los circuitos o separe las canalizaciones)
- `i1_enterrado_D2_columna_defecto`: el motor falló: MissingNormDataError: método D2 (directamente enterrado) con 3 conductores cargados: falta o no corresponde COLUMNA_D2 (None); indique la columna de la Tabla 771.16.VI según la instalación: c1_1x = 1x (columna 1 de la tabla); c4_3x = 3x (columna 4; ver figura de la tabla); c5_3x = 3x (columna 5; ver figura de la tabla). No hay columna por defecto

## Detalle por caso

### a1_vd_trifasica — Caída de tensión trifásica, 100 A, 200 m

- **Estado:** COINCIDE   |   **Gravedad si falla:** importante   |   **Magnitud:** `delta_u_v`
- **Entradas:** I_A = 100, L_m = 200, R_ohm_km = 0.5, X_ohm_km = 0.1, cos_phi = 0.8, Un_V = 400, fases = 3
- **Fórmula y cuenta:** sen(phi)=sqrt(1-0.8^2)=0.6000; R cos+X sen = 0.5*0.8+0.1*0.6000 = 0.4600 ohm/km; dU = sqrt(3)*I*L[km]*(R cos+X sen) = 1.73205*100*0.2*0.4600 = 15.9349 V; dU% = 100*15.9349/400 = 3.9837 %
- **Valor esperado:** 15.9349 V (tolerancia 0.01 %); fuente: `closed_form`
- **Llamada al motor:** `voltage_drop.caida_tension` — fases=3, i_a=I, longitud_m=L, r_ohm_km=R, x_ohm_km=X, fp=cos_phi, un_v=Un
- **Resultado del motor:** 15.9349
- **Diferencia:** +0.000 %
- **Detalle del motor:** dU% = 3.9837 % de 400 V
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Comprueba la fórmula general que usa el pipeline (voltage_drop.caida_tension). Es la misma fórmula; el caso detecta errores de implementación, no de criterio. El porcentaje 3,98 % sobre 400 V se informa aparte.

### b_vd_tabla_vs_formula_1_5mm2 — Tabla 771.19.IV vs fórmula, Cu 1.5 mm2, monofásico cos phi 0,8

- **Estado:** DIFIERE   |   **Gravedad si falla:** menor   |   **Magnitud:** `caida_unitaria_V_por_A_km`
- **Entradas:** S_mm2 = 1.5, R20_ohm_km = 12.1, alpha_Cu_1_K = 0.00393, T_C = 70, X_ohm_km = 0.08, cos_phi = 0.8, fases = 1
- **Fórmula y cuenta:** R70 = R20*(1+alpha*(70-20)) = 12.1*(1+0.00393*50) = 14.4776 ohm/km; sen(phi)=0.6; dU unitaria = 2*(R70*0.8 + X*0.6) = 2*(14.4776*0.8 + 0.08*0.6) = 23.2602 V/(A km)
- **Valor esperado:** 23.2602 V/(A.km) (tolerancia 5.0 %); fuente: `closed_form`
- **Llamada al motor:** `aea_voltage_drop.drop_unit_table` — seccion_mm2=S: valor de la tabla del motor (copia de 771.19.IV)
- **Resultado del motor:** 26
- **Diferencia:** +11.779 %
- **Detalle del motor:** valor de la tabla 771.19.IV copiada en el motor (el pipeline NO la usa: usa la fórmula con R a 70 C)
- **Qué significa:** El motor se aparta del valor de referencia más que la tolerancia. Hay que decidir si el defecto está en el motor o en el criterio del caso. La tabla de la norma está redondeada y la fórmula usa R a 70 C del motor (R20 de IEC 60228 x 1,1965) y X=0,08 del motor. El pipeline dimensiona con la fórmula, no con la tabla; este caso mide cuánto se aparta la tabla de la fórmula. La tolerancia de 5 % es criterio del autor del caso (redondeo de tabla), no de la norma.

### b_vd_tabla_vs_formula_2_5mm2 — Tabla 771.19.IV vs fórmula, Cu 2.5 mm2, monofásico cos phi 0,8

- **Estado:** DIFIERE   |   **Gravedad si falla:** menor   |   **Magnitud:** `caida_unitaria_V_por_A_km`
- **Entradas:** S_mm2 = 2.5, R20_ohm_km = 7.41, alpha_Cu_1_K = 0.00393, T_C = 70, X_ohm_km = 0.08, cos_phi = 0.8, fases = 1
- **Fórmula y cuenta:** R70 = R20*(1+alpha*(70-20)) = 7.41*(1+0.00393*50) = 8.8661 ohm/km; sen(phi)=0.6; dU unitaria = 2*(R70*0.8 + X*0.6) = 2*(8.8661*0.8 + 0.08*0.6) = 14.2817 V/(A km)
- **Valor esperado:** 14.2817 V/(A.km) (tolerancia 5.0 %); fuente: `closed_form`
- **Llamada al motor:** `aea_voltage_drop.drop_unit_table` — seccion_mm2=S: valor de la tabla del motor (copia de 771.19.IV)
- **Resultado del motor:** 15
- **Diferencia:** +5.029 %
- **Detalle del motor:** valor de la tabla 771.19.IV copiada en el motor (el pipeline NO la usa: usa la fórmula con R a 70 C)
- **Qué significa:** El motor se aparta del valor de referencia más que la tolerancia. Hay que decidir si el defecto está en el motor o en el criterio del caso. La tabla de la norma está redondeada y la fórmula usa R a 70 C del motor (R20 de IEC 60228 x 1,1965) y X=0,08 del motor. El pipeline dimensiona con la fórmula, no con la tabla; este caso mide cuánto se aparta la tabla de la fórmula. La tolerancia de 5 % es criterio del autor del caso (redondeo de tabla), no de la norma.

### b_vd_tabla_vs_formula_50mm2 — Tabla 771.19.IV vs fórmula, Cu 50 mm2, monofásico cos phi 0,8

- **Estado:** COINCIDE   |   **Gravedad si falla:** menor   |   **Magnitud:** `caida_unitaria_V_por_A_km`
- **Entradas:** S_mm2 = 50, R20_ohm_km = 0.387, alpha_Cu_1_K = 0.00393, T_C = 70, X_ohm_km = 0.08, cos_phi = 0.8, fases = 1
- **Fórmula y cuenta:** R70 = R20*(1+alpha*(70-20)) = 0.387*(1+0.00393*50) = 0.4630 ohm/km; sen(phi)=0.6; dU unitaria = 2*(R70*0.8 + X*0.6) = 2*(0.4630*0.8 + 0.08*0.6) = 0.8369 V/(A km)
- **Valor esperado:** 0.836873 V/(A.km) (tolerancia 5.0 %); fuente: `closed_form`
- **Llamada al motor:** `aea_voltage_drop.drop_unit_table` — seccion_mm2=S: valor de la tabla del motor (copia de 771.19.IV)
- **Resultado del motor:** 0.8
- **Diferencia:** -4.406 %
- **Detalle del motor:** valor de la tabla 771.19.IV copiada en el motor (el pipeline NO la usa: usa la fórmula con R a 70 C)
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. La tabla de la norma está redondeada y la fórmula usa R a 70 C del motor (R20 de IEC 60228 x 1,1965) y X=0,08 del motor. El pipeline dimensiona con la fórmula, no con la tabla; este caso mide cuánto se aparta la tabla de la fórmula. La tolerancia de 5 % es criterio del autor del caso (redondeo de tabla), no de la norma.

### c1_icc_barra_infinita — Cortocircuito en bornes de trafo 1000 kVA, uk 6 %, red infinita

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `ik_trifasica_inicial_A`
- **Entradas:** Sn_kVA = 1000, uk_pct = 6.0, Un_V = 400.0, c = 1.05, red = "infinita"
- **Fórmula y cuenta:** Z_T = uk/100*Un^2/Sn = 0.06*160000/1e6 = 0.009600 ohm (R_T=0 sin Pcu); Ik'' = c*Un/(sqrt(3)*Z_T) = 1.05*400/(1.73205*0.009600) = 25259.07 A. c = 1,05 = c_fuente_max de los datos del repo (coincide con short_circuit.C_MAX_BT_TOL_6 y aea_pipeline.C_MAX_BT).
- **Valor esperado:** 25259.1 A (tolerancia 0.01 %); fuente: `closed_form`
- **Llamada al motor:** `short_circuit.calcular_ik` — un_v=400, c=factor_c(6), red=None, trafo={sn_va:1e6, uk_pct:6}
- **Resultado del motor:** 25259.1
- **Diferencia:** -0.000 %
- **Detalle del motor:** |Z| = 9.6000 mohm, c = 1.05; R = 0.000e+00, X = 0.00960 ohm
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Verifica la implementación de la impedancia del transformador y de Ik''. El valor de c es el del motor (no se discute aquí la norma).

### d1_icc_red_500MVA — Cortocircuito en bornes de trafo 1000 kVA con red de 500 MVA, X/R 10

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `ik_trifasica_inicial_A`
- **Entradas:** Sn_kVA = 1000, uk_pct = 6.0, Un_V = 400.0, c = 1.05, Sk_MVA = 500, X_R_red = 10.0
- **Fórmula y cuenta:** Z_Q = c*Un^2/Sk = 1.05*160000/5e8 = 3.360000e-04 ohm; R_Q = Z_Q/sqrt(1+10^2) = 3.343325e-05; X_Q = 10*R_Q = 3.343325e-04; Z_T = 0.009600 (puramente reactiva); R = 3.343325e-05, X = 0.009934; |Z| = 0.009934 ohm; Ik'' = c*Un/(sqrt(3)*|Z|) = 24408.86 A
- **Valor esperado:** 24408.9 A (tolerancia 0.01 %); fuente: `closed_form`
- **Llamada al motor:** `short_circuit.calcular_ik` — un_v=400, c=factor_c(6), red={sk_va:5e8, x_r:10}, trafo={sn_va:1e6, uk_pct:6}
- **Resultado del motor:** 24408.9
- **Diferencia:** -0.000 %
- **Detalle del motor:** |Z| = 9.9344 mohm, c = 1.05; R = 3.343e-05, X = 0.00993 ohm
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Verifica la suma de impedancias red + trafo y la descomposición R/X de la red.

### e1_kappa_R0 — Factor de pico kappa con R/X = 0

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `kappa`
- **Entradas:** R_ohm = 0.0, X_ohm = 0.0096
- **Fórmula y cuenta:** kappa = 1.02 + 0.98*exp(-3*R/X) = 1.02 + 0.98*exp(0) = 2.00
- **Valor esperado:** 2 - (tolerancia 0.01 %); fuente: `closed_form`
- **Llamada al motor:** `short_circuit.factor_kappa` — r_ohm=R, x_ohm=X
- **Resultado del motor:** 2
- **Diferencia:** +0.000 %
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. La fórmula de kappa es la que declara el motor ([VERIFICAR] en su código); el caso verifica límites y la implementación, no el valor normativo de la fórmula.

### e2_kappa_R_X_0_1 — Factor de pico kappa con R/X = 0,1

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `kappa`
- **Entradas:** R_ohm = 0.00096, X_ohm = 0.0096
- **Fórmula y cuenta:** kappa = 1.02 + 0.98*exp(-3*0.1) = 1.02 + 0.98*0.740818 = 1.746002
- **Valor esperado:** 1.746 - (tolerancia 0.01 %); fuente: `closed_form`
- **Llamada al motor:** `short_circuit.factor_kappa` — r_ohm=R, x_ohm=X
- **Resultado del motor:** 1.746
- **Diferencia:** -0.000 %
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Idem e1.

### e3_kappa_X0 — Factor de pico kappa con X = 0 (R>0)

- **Estado:** COINCIDE   |   **Gravedad si falla:** menor   |   **Magnitud:** `kappa`
- **Entradas:** R_ohm = 0.01, X_ohm = 0.0
- **Fórmula y cuenta:** Límite R/X -> infinito: exp(-3*R/X) -> 0, kappa -> 1.02. (El cociente R/X no se puede evaluar con X=0; se toma el límite.)
- **Valor esperado:** 1.02 - (tolerancia 0.01 %); fuente: `closed_form`
- **Llamada al motor:** `short_circuit.factor_kappa` — r_ohm=R, x_ohm=X
- **Resultado del motor:** 1.02
- **Diferencia:** +0.000 %
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Caso límite: el motor devuelve 1,02 sin dividir por cero.

### e4_corriente_pico_barra_infinita — Corriente de pico en el caso c1 (R=0)

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `ip_A`
- **Entradas:** Ik_A = 25259.0743, R_ohm = 0.0, X_ohm = 0.0096
- **Fórmula y cuenta:** ip = kappa*sqrt(2)*Ik'' = 2.00*1.41421*25259.07 = 71443.45 A
- **Valor esperado:** 71443.5 A (tolerancia 0.01 %); fuente: `closed_form`
- **Llamada al motor:** `short_circuit.corriente_pico` — ik_a, r_ohm, x_ohm del caso c1 (calcular_ik)
- **Resultado del motor:** 71443.5
- **Diferencia:** +0.000 %
- **Detalle del motor:** Ik'' = 25259.07 A; kappa = 2.0000
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Poder de cierre: la corriente de pico es la que define el esfuerzo electrodinámico y el poder de cierre.

### f1_adiabatica_10kA_1s_sobre300 — Sección mínima adiabática Cu/PVC para cable de más de 300 mm2, 10 kA, 1 s

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `s_min_mm2`
- **Entradas:** I_A = 10000.0, t_s = 1.0, k = 103.0, material = "Cu", aislacion = "PVC", seccion_cable = "> 300 mm2"
- **Fórmula y cuenta:** S_min = I*sqrt(t)/k = 10000*sqrt(1)/103.0 = 97.087 mm2, con k = 103.0 (clave pvc_sobre_300|cu de los datos del repo). El motor cable_thermal usa k = 115 (plano, sin distinguir sección).
- **Valor esperado:** 97.0874 mm2 (tolerancia 0.5 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_tables.json#/constantes/771.19.II_k_adiabatico/pvc_sobre_300|cu`
- **Llamada al motor:** `cable_thermal.seccion_minima_mm2` — i_cc_a=I, t_s=t, k=k_material('Cu','PVC')
- **Resultado del motor:** 97.0874
- **Diferencia:** -0.000 %
- **Detalle del motor:** cable_thermal usa k = 103.0 (sección 301.0); aea_conductors.k_adiabatico_771('pvc_sobre_300','cu') = 103.0 y ('pvc_hasta_300','cu') = 115.0
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Con 10 kA la sección mínima (97 mm2) queda por debajo de 300 mm2: la premisa 'cable de más de 300 mm2' es hipotética; el caso f2 (40 kA) la hace coherente. El módulo cable_thermal no tiene el k reducido para secciones mayores de 300 mm2 que sí tienen los datos (aea_conductors.k_adiabatico_771 lo tiene). Un k mayor subestima la sección mínima (lado inseguro).

### f2_adiabatica_40kA_1s_sobre300 — Sección mínima adiabática Cu/PVC para cable de más de 300 mm2, 40 kA, 1 s

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `s_min_mm2`
- **Entradas:** I_A = 40000.0, t_s = 1.0, k = 103.0, material = "Cu", aislacion = "PVC", seccion_cable = "> 300 mm2"
- **Fórmula y cuenta:** S_min = I*sqrt(t)/k = 40000*sqrt(1)/103.0 = 388.350 mm2, con k = 103.0 (clave pvc_sobre_300|cu de los datos del repo). El motor cable_thermal usa k = 115 (plano, sin distinguir sección).
- **Valor esperado:** 388.35 mm2 (tolerancia 0.5 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_tables.json#/constantes/771.19.II_k_adiabatico/pvc_sobre_300|cu`
- **Llamada al motor:** `cable_thermal.seccion_minima_mm2` — i_cc_a=I, t_s=t, k=k_material('Cu','PVC')
- **Resultado del motor:** 388.35
- **Diferencia:** -0.000 %
- **Detalle del motor:** cable_thermal usa k = 103.0 (sección 301.0); aea_conductors.k_adiabatico_771('pvc_sobre_300','cu') = 103.0 y ('pvc_hasta_300','cu') = 115.0
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Aquí la sección mínima supera 300 mm2, así que la premisa es coherente. El módulo cable_thermal no tiene el k reducido para secciones mayores de 300 mm2 que sí tienen los datos (aea_conductors.k_adiabatico_771 lo tiene). Un k mayor subestima la sección mínima (lado inseguro).

### g1_iz_base — Iz base Cu 2,5 mm2 PVC B1, 3 cargados, 40 C

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `iz_a`
- **Entradas:** aislacion = "PVC", material = "Cu", metodo = "B1", S_mm2 = 2.5, cargados = 3, agrupamiento = 1, temp_C = 40
- **Fórmula y cuenta:** Iz = valor de la Tabla 771.16.I (fila 2,5 mm2, columna 3x) = 18 A (sin factores)
- **Valor esperado:** 18 A (tolerancia 0.01 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_tables.json#/tablas_capacidad/771.16.I/bloques/0/filas/cu/2.5/1`
- **Llamada al motor:** `aea_ampacity.iz` — AMP.parametros({AISLACION:'pvc', MATERIAL:'cu', METODO:'B1', AGRUP_CIRCUITOS, TEMP_AMBIENTE_C}); iz(par, 2.5, fases=3)
- **Resultado del motor:** 18
- **Diferencia:** +0.000 %
- **Detalle del motor:** factores del motor: {'f_clase': 1.0, 'f_temp': 1.0, 'f_agrup': 1.0, 'f_suelo': 1.0}; Iz base = 18.0 A
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Lectura directa de la tabla del repo.

### g2_iz_agrupamiento3 — Iz con 3 circuitos trifásicos en un caño

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `iz_a`
- **Entradas:** aislacion = "PVC", material = "Cu", metodo = "B1", S_mm2 = 2.5, cargados = 3, agrupamiento = 3, temp_C = 40
- **Fórmula y cuenta:** Iz = 18 * 0.7 = 12.6000 A
- **Valor esperado:** 12.6 A (tolerancia 0.01 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_tables.json#/factores_correccion/771.16.II.b/filas/3/factor`
- **Llamada al motor:** `aea_ampacity.iz` — AMP.parametros({AISLACION:'pvc', MATERIAL:'cu', METODO:'B1', AGRUP_CIRCUITOS, TEMP_AMBIENTE_C}); iz(par, 2.5, fases=3)
- **Resultado del motor:** 12.6
- **Diferencia:** +0.000 %
- **Detalle del motor:** factores del motor: {'f_clase': 1.0, 'f_temp': 1.0, 'f_agrup': 0.7, 'f_suelo': 1.0}; Iz base = 18.0 A
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Producto manual de dos valores del repo.

### g3_iz_temp50 — Iz a 50 C ambiente

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `iz_a`
- **Entradas:** aislacion = "PVC", material = "Cu", metodo = "B1", S_mm2 = 2.5, cargados = 3, agrupamiento = 1, temp_C = 50
- **Fórmula y cuenta:** Iz = 18 * 0.82 = 14.7600 A
- **Valor esperado:** 14.76 A (tolerancia 0.01 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_tables.json#/factores_correccion/771.16.II.a/factores/pvc/8`
- **Llamada al motor:** `aea_ampacity.iz` — AMP.parametros({AISLACION:'pvc', MATERIAL:'cu', METODO:'B1', AGRUP_CIRCUITOS, TEMP_AMBIENTE_C}); iz(par, 2.5, fases=3)
- **Resultado del motor:** 14.76
- **Diferencia:** +0.000 %
- **Detalle del motor:** factores del motor: {'f_clase': 1.0, 'f_temp': 0.82, 'f_agrup': 1.0, 'f_suelo': 1.0}; Iz base = 18.0 A
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Producto manual de dos valores del repo.

### g4_iz_combinada — Iz con 3 circuitos agrupados y 50 C

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `iz_a`
- **Entradas:** aislacion = "PVC", material = "Cu", metodo = "B1", S_mm2 = 2.5, cargados = 3, agrupamiento = 3, temp_C = 50
- **Fórmula y cuenta:** Iz = 18 * 0.7 * 0.82 = 10.3320 A
- **Valor esperado:** 10.332 A (tolerancia 0.01 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_tables.json#/tablas_capacidad/771.16.I/bloques/0/filas/cu/2.5/1`
- **Llamada al motor:** `aea_ampacity.iz` — AMP.parametros({AISLACION:'pvc', MATERIAL:'cu', METODO:'B1', AGRUP_CIRCUITOS, TEMP_AMBIENTE_C}); iz(par, 2.5, fases=3)
- **Resultado del motor:** 10.332
- **Diferencia:** -0.000 %
- **Detalle del motor:** factores del motor: {'f_clase': 1.0, 'f_temp': 0.82, 'f_agrup': 0.7, 'f_suelo': 1.0}; Iz base = 18.0 A
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Producto manual de tres valores del repo; ver si el motor aplica ambos factores.

### h1_agrupamiento_aire_entre_conteos — Agrupamiento en aire con 10 circuitos (entre 9 y 12 tabulados)

- **Estado:** NO CORRIÓ   |   **Gravedad si falla:** importante   |   **Magnitud:** `f_agrup`
- **Entradas:** metodo = "B1", circuitos = 10, trifasicos = true, tabulados = [1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 16, 20], factores = [1.0, 0.8, 0.7, 0.65, 0.6, 0.57, 0.54, 0.52, 0.5, 0.45, 0.41, 0.38]
- **Fórmula y cuenta:** La tabla (item 1) trae 9 -> 0.5 y 12 -> 0.45; no trae 10. Interpolación lineal = 0.5 + (0.45-0.5)*(10-9)/(12-9) = 0.48333; criterio conservador (siguiente conteo tabulado, 12) = 0.45; criterio 'último conteo cubierto' (9) = 0.5. La norma decide cuál; no hay valor esperado.
- **Valor esperado:** ninguno (decisión del dueño)
- **Llamada al motor:** `aea_ampacity.factores` — par(B1, AGRUP_CIRCUITOS=10); factores(par, True)['f_agrup']
- **Resultado del motor:** no corrió: el motor falló: MissingNormDataError: agrupamiento de 10 circuitos fuera de la Tabla 771.16.IV (ítem 1): la tabla trae solo [2, 3, 4, 5, 6, 7, 8, 9, 12, 16, 20] circuitos; no se interpola ni se repite el último factor. Indique en AGRUP_CIRCUITOS uno de esos números (reagrupe los circuitos o separe las canalizaciones)
- **Diferencia:** -
- **Qué significa:** El adaptador no pudo llamar al motor; no hay comparación. El motor interpola linealmente. Si el texto oficial manda tomar el siguiente conteo (más conservador), el motor da Iz hasta 7 % mayor. Decisión del dueño / texto oficial.

### h2_agrupamiento_enterrado_7 — Agrupamiento de 7 circuitos directamente enterrados (D2), fuera de la tabla

- **Estado:** NO CORRIÓ   |   **Gravedad si falla:** importante   |   **Magnitud:** `f_agrup`
- **Entradas:** metodo = "D2", circuitos = 7, separacion = "en contacto (columna 0)"
- **Fórmula y cuenta:** La tabla VII.c llega a 6 circuitos (0,5 en contacto). Para 7 o más el motor usa la fila de 6 (min(n,6)) sin aviso. Qué factor corresponde a más de 6 lo decide el texto oficial.
- **Valor esperado:** ninguno (decisión del dueño)
- **Llamada al motor:** `aea_ampacity.factores` — par(D2, AGRUP_CIRCUITOS=7); factores(par, True)['f_agrup']
- **Resultado del motor:** no corrió: el motor falló: MissingNormDataError: falta la separación entre cables (SEPARACION_CABLES) de la Tabla 771.16.VII.c: indique una de ['en contacto', '1 diámetro', '0,125 m', '0,25 m', '0,5 m']; no hay columna por defecto
- **Diferencia:** -
- **Qué significa:** El adaptador no pudo llamar al motor; no hay comparación. Fuera de tabla el motor no avisa ni rechaza: repite el último valor. Para el aire sí repite el último (item 1) también sin aviso. Decisión del dueño.

### h3_agrupamiento_aire_25 — Agrupamiento en aire con 25 circuitos (más que el último conteo, 20)

- **Estado:** NO CORRIÓ   |   **Gravedad si falla:** importante   |   **Magnitud:** `f_agrup`
- **Entradas:** metodo = "B1", circuitos = 25, ultimo_tabulado = 20
- **Fórmula y cuenta:** La tabla termina en 20 circuitos (0,38). El motor usa 0,38 para cualquier n > 20.
- **Valor esperado:** ninguno (decisión del dueño)
- **Llamada al motor:** `aea_ampacity.factores` — par(B1, AGRUP_CIRCUITOS=25); factores(par, True)['f_agrup']
- **Resultado del motor:** no corrió: el motor falló: MissingNormDataError: agrupamiento de 25 circuitos fuera de la Tabla 771.16.IV (ítem 1): la tabla trae solo [2, 3, 4, 5, 6, 7, 8, 9, 12, 16, 20] circuitos; no se interpola ni se repite el último factor. Indique en AGRUP_CIRCUITOS uno de esos números (reagrupe los circuitos o separe las canalizaciones)
- **Diferencia:** -
- **Qué significa:** El adaptador no pudo llamar al motor; no hay comparación. Sin aviso fuera de rango. Decisión del dueño.

### i1_enterrado_D2_columna_defecto — Enterrado D2, Cu 1,5 mm2 PVC, 3 cargados, sin dato de instalación: columna por defecto

- **Estado:** NO CORRIÓ   |   **Gravedad si falla:** importante   |   **Magnitud:** `iz_a`
- **Entradas:** metodo = "D2", aislacion = "PVC", material = "Cu", S_mm2 = 1.5, cargados = 3
- **Fórmula y cuenta:** Valores de la Tabla 771.16.VI para 1,5 mm2 Cu PVC: c1_1x (3 cargados)=30; c2_2x (2 cargados)=29; c3_2x (2 cargados)=25; c4_3x (3 cargados)=25; c5_3x (3 cargados)=20. Con 3 cargados hay tres columnas posibles (20, 25, 30 A); el motor elige c4_3x (25 A, comentario 'a confirmar'). Cuál corresponde depende de la figura de instalación que el motor no pide.
- **Valor esperado:** ninguno (decisión del dueño)
- **Llamada al motor:** `aea_ampacity.iz` — par(D2); iz(par, 1.5, 3)
- **Resultado del motor:** no corrió: el motor falló: MissingNormDataError: método D2 (directamente enterrado) con 3 conductores cargados: falta o no corresponde COLUMNA_D2 (None); indique la columna de la Tabla 771.16.VI según la instalación: c1_1x = 1x (columna 1 de la tabla); c4_3x = 3x (columna 4; ver figura de la tabla); c5_3x = 3x (columna 5; ver figura de la tabla). No hay columna por defecto
- **Diferencia:** -
- **Qué significa:** El adaptador no pudo llamar al motor; no hay comparación. El valor por defecto (25 A) no es el más conservador (20 A). Hay que decidir si se exige el dato de instalación o se adopta la columna más desfavorable.

### j_tt_ra_300ma_earthing — Ra máxima TT con IΔn = 300 mA (earthing)

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `ra_max_ohm`
- **Entradas:** I_dn_A = 0.3, esquema = "TT"
- **Fórmula y cuenta:** Dato del repo: tabla de reglas/puesta_a_tierra.json, fila IΔn=0.3 A, columna 3 (Ra máximo permitido) = 40 ohm; coincide con min(0,5*24/IΔn, 40) = min(40.0, 40) = 40.0 ohm y con la constante 771.18_ra_max_ohm = 40.
- **Valor esperado:** 40 ohm (tolerancia 0.5 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/rules/puesta_a_tierra.json#/reglas/1/tabla/filas/6/3`
- **Llamada al motor:** `aea_earthing.ra_maxima` — i_dn_a=IΔn; ['adoptada']
- **Resultado del motor:** 40
- **Diferencia:** +0.000 %
- **Detalle del motor:** col1 (50 V) = 166.7, col2 (24 V) = 80.0, adoptada = 40.0 ohm
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Camino del módulo de puesta a tierra.

### j_tt_ra_300ma_memo — Ra máxima TT con IΔn = 300 mA (memo)

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `ra_max_ohm`
- **Entradas:** I_dn_A = 0.3, esquema = "TT"
- **Fórmula y cuenta:** Dato del repo: tabla de reglas/puesta_a_tierra.json, fila IΔn=0.3 A, columna 3 (Ra máximo permitido) = 40 ohm; coincide con min(0,5*24/IΔn, 40) = min(40.0, 40) = 40.0 ohm y con la constante 771.18_ra_max_ohm = 40.
- **Valor esperado:** 40 ohm (tolerancia 0.5 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/rules/puesta_a_tierra.json#/reglas/1/tabla/filas/6/3`
- **Llamada al motor:** `board_memo._circuit (campo diferencial.ra_max_tt_ohm)` — construye un circuito de tomacorrientes con RCD y lee diferencial.ra_max_tt_ohm
- **Resultado del motor:** 40
- **Diferencia:** +0.000 %
- **Detalle del motor:** diferencial del memo = {'tag_rcd': 'T1', 'idn_ma': 300.0, 'tipo': 'A', 'esquema': 'TT', 'zs_max_ohm': 697.0, 'ra_max_tt_ohm': 40.0, 'contacto_indirecto': True, 'cumple': True}; el memo usa aea_earthing.ra_maxima (D11)
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. La memoria imprime Ra máx = UL_V/IΔn con UL_V = 50 V y sin tope de 40 ohm: el documento entregado al cliente mostraría un valor muy superior al de la regla del repo.

### j_tt_ra_300ma_protection — Ra máxima TT con IΔn = 300 mA (protection)

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `ra_max_ohm`
- **Entradas:** I_dn_A = 0.3, esquema = "TT"
- **Fórmula y cuenta:** Dato del repo: tabla de reglas/puesta_a_tierra.json, fila IΔn=0.3 A, columna 3 (Ra máximo permitido) = 40 ohm; coincide con min(0,5*24/IΔn, 40) = min(40.0, 40) = 40.0 ohm y con la constante 771.18_ra_max_ohm = 40.
- **Valor esperado:** 40 ohm (tolerancia 0.5 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/rules/puesta_a_tierra.json#/reglas/1/tabla/filas/6/3`
- **Llamada al motor:** `aea_protection.ra_maxima_tt` — ia_a=IΔn (ul_v por defecto 50 V)
- **Resultado del motor:** 40
- **Diferencia:** +0.000 %
- **Detalle del motor:** ra_maxima_tt(ia_a): la Ra adoptada de aea_earthing.ra_maxima (D11)
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. aea_protection.ra_maxima_tt usa UL=50 V por defecto y no aplica el tope de 40 ohm: da una Ra máxima muy mayor que la regla del repo (lado inseguro si se usa para verificar una puesta a tierra).

### j_tt_ra_30ma_earthing — Ra máxima TT con IΔn = 30 mA (earthing)

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `ra_max_ohm`
- **Entradas:** I_dn_A = 0.03, esquema = "TT"
- **Fórmula y cuenta:** Dato del repo: tabla de reglas/puesta_a_tierra.json, fila IΔn=0.03 A, columna 3 (Ra máximo permitido) = 40 ohm; coincide con min(0,5*24/IΔn, 40) = min(400.0, 40) = 40.0 ohm y con la constante 771.18_ra_max_ohm = 40.
- **Valor esperado:** 40 ohm (tolerancia 0.5 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/rules/puesta_a_tierra.json#/reglas/1/tabla/filas/8/3`
- **Llamada al motor:** `aea_earthing.ra_maxima` — i_dn_a=IΔn; ['adoptada']
- **Resultado del motor:** 40
- **Diferencia:** +0.000 %
- **Detalle del motor:** col1 (50 V) = 1666.7, col2 (24 V) = 800.0, adoptada = 40.0 ohm
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Camino del módulo de puesta a tierra.

### j_tt_ra_30ma_memo — Ra máxima TT con IΔn = 30 mA (memo)

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `ra_max_ohm`
- **Entradas:** I_dn_A = 0.03, esquema = "TT"
- **Fórmula y cuenta:** Dato del repo: tabla de reglas/puesta_a_tierra.json, fila IΔn=0.03 A, columna 3 (Ra máximo permitido) = 40 ohm; coincide con min(0,5*24/IΔn, 40) = min(400.0, 40) = 40.0 ohm y con la constante 771.18_ra_max_ohm = 40.
- **Valor esperado:** 40 ohm (tolerancia 0.5 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/rules/puesta_a_tierra.json#/reglas/1/tabla/filas/8/3`
- **Llamada al motor:** `board_memo._circuit (campo diferencial.ra_max_tt_ohm)` — construye un circuito de tomacorrientes con RCD y lee diferencial.ra_max_tt_ohm
- **Resultado del motor:** 40
- **Diferencia:** +0.000 %
- **Detalle del motor:** diferencial del memo = {'tag_rcd': 'T1', 'idn_ma': 30.0, 'tipo': 'A', 'esquema': 'TT', 'zs_max_ohm': 6967.0, 'ra_max_tt_ohm': 40.0, 'contacto_indirecto': True, 'cumple': True}; el memo usa aea_earthing.ra_maxima (D11)
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. La memoria imprime Ra máx = UL_V/IΔn con UL_V = 50 V y sin tope de 40 ohm: el documento entregado al cliente mostraría un valor muy superior al de la regla del repo.

### j_tt_ra_30ma_protection — Ra máxima TT con IΔn = 30 mA (protection)

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `ra_max_ohm`
- **Entradas:** I_dn_A = 0.03, esquema = "TT"
- **Fórmula y cuenta:** Dato del repo: tabla de reglas/puesta_a_tierra.json, fila IΔn=0.03 A, columna 3 (Ra máximo permitido) = 40 ohm; coincide con min(0,5*24/IΔn, 40) = min(400.0, 40) = 40.0 ohm y con la constante 771.18_ra_max_ohm = 40.
- **Valor esperado:** 40 ohm (tolerancia 0.5 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/rules/puesta_a_tierra.json#/reglas/1/tabla/filas/8/3`
- **Llamada al motor:** `aea_protection.ra_maxima_tt` — ia_a=IΔn (ul_v por defecto 50 V)
- **Resultado del motor:** 40
- **Diferencia:** +0.000 %
- **Detalle del motor:** ra_maxima_tt(ia_a): la Ra adoptada de aea_earthing.ra_maxima (D11)
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. aea_protection.ra_maxima_tt usa UL=50 V por defecto y no aplica el tope de 40 ohm: da una Ra máxima muy mayor que la regla del repo (lado inseguro si se usa para verificar una puesta a tierra).

### k1_tiempos_desconexion_duplicado — Tiempos máximos de desconexión: motor vs datos del repo

- **Estado:** SIN VALOR OFICIAL   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `entradas_distintas`
- **Entradas:** fuente_motor = "aea_earthing.TIEMPOS_DESCONEXION_S (rotulada Tabla 771.18.I)", fuente_repo = "aea_tables.json constantes 771.18.III_tiempos_desconexion_s"
- **Fórmula y cuenta:** Se compara entrada por entrada (esquema, rango de tensión, ca, cc). El valor oficial de cada tiempo solo lo da el texto de la norma: no se fija valor esperado. Además el motor rotula la tabla 771.18.I y los datos 771.18.III.
- **Valor esperado:** ninguno (valor oficial pendiente)
- **Llamada al motor:** `aea_earthing.tiempo_desconexion_max_s / TIEMPOS_DESCONEXION_S` — compara la constante del módulo con la de aea_tables.json
- **Resultado del motor:** 0
- **Diferencia:** -
- **Detalle del motor:** 18 valores comparados, 0 distintos; el motor rotula la tabla como 771.18.I y los datos como 771.18.III
- **Qué significa:** No hay valor esperado: solo el texto oficial o una decisión del dueño lo fija. Se muestra qué hace hoy el motor. Es un dato duplicado en dos lugares (viola 'una sola fuente de la verdad'). Si hoy son iguales, el riesgo es que diverjan. El valor oficial hay que confirmarlo con el texto.

### l1_tn_zs_lazo — Lazo TN: Zs al final de 150 m, 2,5 mm2 fase y PE, Icc barras 2 kA

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `zs_ohm`
- **Entradas:** L_m = 150.0, S_fase_mm2 = 2.5, S_PE_mm2 = 2.5, Icc_barras_kA = 2.0, U0_V = 230.0, protección = "C16", Ia_A = 160.0
- **Fórmula y cuenta:** R70 = R20*(1+alpha*50) = 7.41*(1+0.00393*50) = 8.8661 ohm/km; R lazo = (R_fase+R_PE)*L = 2*8.8661*0.15 = 2.6598 ohm; X lazo = 0.08*0.15 = 0.0120 ohm; Z fuente = c*U0/Icc = 1.05*230/2000 = 0.12075 ohm; Zs = |(Z_fuente+R) + jX| = hypot(2.78057, 0.0120) = 2.78060 ohm. (alpha_Cu = 0,00393 /K es dato declarado del caso; el motor usa un factor plano 1,2.)
- **Valor esperado:** 2.78059 ohm (tolerancia 1.0 %); fuente: `closed_form`
- **Llamada al motor:** `aea_earthing.zs_lazo` — u0_v=230, icc_barras_ka=2, s_fase_mm2=2.5, s_pe_mm2=2.5, largo_m=150
- **Resultado del motor:** 2.78838
- **Diferencia:** +0.280 %
- **Detalle del motor:** Z fuente = 0.12075, R lazo = 2.6676, X lazo = 0.0120 ohm
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. El motor usa 1,2 como factor de temperatura (equivale a unos 71 C); con alpha a 70 C da 1,1965: 0,3 % de diferencia en R. Tolerancia 1 % (criterio del autor).

### l2_tn_zs_maxima — Zs máxima para disparo magnético C16 (Ia = 10 x In = 160 A)

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `zs_max_ohm`
- **Entradas:** U0_V = 230.0, Ia_A = 160.0, c_min = 0.95
- **Fórmula y cuenta:** Zs_max = c_min*U0/Ia = 0.95*230/160 = 1.36563 ohm (c_min = c_tension_min de los datos del repo; Ia = 10*16 = 160 A es dato del caso: curva C, múltiplo máximo que usa el pipeline en K_MAGNETICO_C)
- **Valor esperado:** 1.36563 ohm (tolerancia 0.01 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_tables.json#/constantes/impedancias_estandar/c_tension_min`
- **Llamada al motor:** `aea_earthing.zs_maxima` — u0_v=230, ia_a=160
- **Resultado del motor:** 1.36563
- **Diferencia:** +0.000 %
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Chequeo de implementación.

### l3_tn_verifica_producto — Lazo TN: Zs x Ia frente a U0 (el caso debe FALLAR)

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `zs_ia_V`
- **Entradas:** L_m = 150.0, S_fase_mm2 = 2.5, S_PE_mm2 = 2.5, Icc_barras_kA = 2.0, U0_V = 230.0, protección = "C16", Ia_A = 160.0, nota = "U0 = 230 V"
- **Fórmula y cuenta:** Zs x Ia = 2.78060*160 = 444.90 V > U0 = 230 V -> no cumple (Zs 2.781 ohm > Zs_max 1.366 ohm). Se espera que el motor reporte 'no cumple'.
- **Valor esperado:** 444.895 V (tolerancia 1.0 %); fuente: `closed_form`
- **Llamada al motor:** `aea_protection.verifica_tn` — zs = aea_earthing.zs_lazo(...)['zs_ohm'], ia_a=160, u0_v=230; lee zs_ia_v y cumple
- **Resultado del motor:** 446.14
- **Diferencia:** +0.280 %
- **Detalle del motor:** verifica_tn: cumple = False (límite 218.5 V); se espera cumple = False
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Si el motor dijera 'cumple' sería un defecto de seguridad; se informa también el veredicto.

### l4_tn_limite_zs_inconsistente — Límite de Zs: verifica_tn (U0/Ia) frente a zs_maxima (c_min x U0/Ia)

- **Estado:** SIN VALOR OFICIAL   |   **Gravedad si falla:** importante   |   **Magnitud:** `zs_limite_ohm`
- **Entradas:** U0_V = 230.0, Ia_A = 160.0
- **Fórmula y cuenta:** verifica_tn compara Zs*Ia con U0 -> Zs <= 1.43750 ohm; zs_maxima da 0.95*U0/Ia = 1.36563 ohm. Difieren 5.26 %. Cuál es el límite correcto (con o sin c_min) lo decide el texto oficial.
- **Valor esperado:** ninguno (valor oficial pendiente)
- **Llamada al motor:** `aea_protection.verifica_tn` — compara limite_v/ia_a de verifica_tn con aea_earthing.zs_maxima
- **Resultado del motor:** 1.36563
- **Diferencia:** -
- **Detalle del motor:** verifica_tn: Zs <= 1.36563 ohm; zs_maxima: 1.36563 ohm; diferencia 0.00 %
- **Qué significa:** No hay valor esperado: solo el texto oficial o una decisión del dueño lo fija. Se muestra qué hace hoy el motor. Dos criterios distintos para la misma verificación dentro del motor.

### m_jabalina_continuidad_L_d_100 — Continuidad del modo simplificado en el borde L/d = 100

- **Estado:** DIFIERE   |   **Gravedad si falla:** menor   |   **Magnitud:** `salto_relativo_pct`
- **Entradas:** rho_ohm_m = 100.0, L_m = 3.0, d_antes_m = 0.03, d_despues_m = 0.0299, L_d_antes = 100.0, L_d_despues = 100.33444816053512
- **Fórmula y cuenta:** La resistencia real de una jabalina varía de forma continua con d: según Dwight R(0.03)=30.1578 y R(0.0299)=30.1755, salto = +0.059 %. Se espera un salto cercano a 0; la tolerancia es 1 punto porcentual absoluto.
- **Valor esperado:** 0.058736 % (puntos) (tolerancia 1.0 pp); fuente: `closed_form`
- **Llamada al motor:** `aea_earthing.resistance_rod` — salto % entre simplificada(d_despues) y simplificada(d_antes)
- **Resultado del motor:** 33.3333
- **Diferencia:** +33.275 pp
- **Detalle del motor:** simplificada: R(100) = 25.0000 ohm, R(100.33) = 33.3333 ohm
- **Qué significa:** El motor se aparta del valor de referencia más que la tolerancia. Hay que decidir si el defecto está en el motor o en el criterio del caso. El factor k de la simplificada es escalonado (0,75 / 1,0 / 1,2): en el borde la resistencia salta de golpe. Solo ocurre con simplificada=True.

### m_jabalina_continuidad_L_d_600 — Continuidad del modo simplificado en el borde L/d = 600

- **Estado:** DIFIERE   |   **Gravedad si falla:** menor   |   **Magnitud:** `salto_relativo_pct`
- **Entradas:** rho_ohm_m = 100.0, L_m = 3.0, d_antes_m = 0.005, d_despues_m = 0.0049, L_d_antes = 600.0, L_d_despues = 612.2448979591837
- **Fórmula y cuenta:** La resistencia real de una jabalina varía de forma continua con d: según Dwight R(0.005)=39.6634 y R(0.0049)=39.7706, salto = +0.270 %. Se espera un salto cercano a 0; la tolerancia es 1 punto porcentual absoluto.
- **Valor esperado:** 0.270221 % (puntos) (tolerancia 1.0 pp); fuente: `closed_form`
- **Llamada al motor:** `aea_earthing.resistance_rod` — salto % entre simplificada(d_despues) y simplificada(d_antes)
- **Resultado del motor:** 20
- **Diferencia:** +19.730 pp
- **Detalle del motor:** simplificada: R(600) = 33.3333 ohm, R(612.24) = 40.0000 ohm
- **Qué significa:** El motor se aparta del valor de referencia más que la tolerancia. Hay que decidir si el defecto está en el motor o en el criterio del caso. El factor k de la simplificada es escalonado (0,75 / 1,0 / 1,2): en el borde la resistencia salta de golpe. Solo ocurre con simplificada=True.

### m_jabalina_dwight_d10mm — Jabalina rho 100, L 3 m, d 10 mm: fórmula de Dwight

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `r_ohm`
- **Entradas:** rho_ohm_m = 100.0, L_m = 3.0, d_m = 0.01
- **Fórmula y cuenta:** R = rho/(2*pi*L)*(ln(8L/d)-1) = 100/(2*pi*3)*(ln(2400)-1) = 5.30516*(7.78322-1) = 35.9861 ohm
- **Valor esperado:** 35.9861 ohm (tolerancia 0.01 %); fuente: `closed_form`
- **Llamada al motor:** `aea_earthing.resistance_rod` — rho, largo_m=L, diametro_m=d, simplificada=False
- **Resultado del motor:** 35.9861
- **Diferencia:** +0.000 %
- **Detalle del motor:** L/d = 300
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Fórmula exacta (modo por defecto).

### m_jabalina_dwight_d30mm — Jabalina rho 100, L 3 m, d 30 mm: fórmula de Dwight

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `r_ohm`
- **Entradas:** rho_ohm_m = 100.0, L_m = 3.0, d_m = 0.03
- **Fórmula y cuenta:** R = rho/(2*pi*L)*(ln(8L/d)-1) = 100/(2*pi*3)*(ln(800)-1) = 5.30516*(6.68461-1) = 30.1578 ohm
- **Valor esperado:** 30.1578 ohm (tolerancia 0.01 %); fuente: `closed_form`
- **Llamada al motor:** `aea_earthing.resistance_rod` — rho, largo_m=L, diametro_m=d, simplificada=False
- **Resultado del motor:** 30.1578
- **Diferencia:** -0.000 %
- **Detalle del motor:** L/d = 100
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Fórmula exacta (modo por defecto).

### m_jabalina_simplificada_d10mm — Jabalina simplificada vs Dwight, L/d = 300

- **Estado:** DIFIERE   |   **Gravedad si falla:** menor   |   **Magnitud:** `r_ohm`
- **Entradas:** rho_ohm_m = 100.0, L_m = 3.0, d_m = 0.01, modo = "simplificada"
- **Fórmula y cuenta:** Referencia exacta (Dwight) = 35.9861 ohm. El modo simplificado del motor usa k*rho/L con k = 1.0 para L/d = 300: 33.3333 ohm (-7.4 % respecto de Dwight).
- **Valor esperado:** 35.9861 ohm (tolerancia 5.0 %); fuente: `closed_form`
- **Llamada al motor:** `aea_earthing.resistance_rod` — rho, largo_m=L, diametro_m=d, simplificada=True
- **Resultado del motor:** 33.3333
- **Diferencia:** -7.372 %
- **Detalle del motor:** L/d = 300 (modo simplificado)
- **Qué significa:** El motor se aparta del valor de referencia más que la tolerancia. Hay que decidir si el defecto está en el motor o en el criterio del caso. El modo simplificado es una aproximación de la norma; la tolerancia de 5 % es criterio del autor del caso.

### m_jabalina_simplificada_d30mm — Jabalina simplificada vs Dwight, L/d = 100

- **Estado:** DIFIERE   |   **Gravedad si falla:** menor   |   **Magnitud:** `r_ohm`
- **Entradas:** rho_ohm_m = 100.0, L_m = 3.0, d_m = 0.03, modo = "simplificada"
- **Fórmula y cuenta:** Referencia exacta (Dwight) = 30.1578 ohm. El modo simplificado del motor usa k*rho/L con k = 0.75 para L/d = 100: 25.0000 ohm (-17.1 % respecto de Dwight).
- **Valor esperado:** 30.1578 ohm (tolerancia 5.0 %); fuente: `closed_form`
- **Llamada al motor:** `aea_earthing.resistance_rod` — rho, largo_m=L, diametro_m=d, simplificada=True
- **Resultado del motor:** 25
- **Diferencia:** -17.103 %
- **Detalle del motor:** L/d = 100 (modo simplificado)
- **Qué significa:** El motor se aparta del valor de referencia más que la tolerancia. Hay que decidir si el defecto está en el motor o en el criterio del caso. El modo simplificado es una aproximación de la norma; la tolerancia de 5 % es criterio del autor del caso.

### n1_reactiva_qc — Banco de capacitores: reactiva a compensar, 100 kW de 0,70 a 0,95

- **Estado:** COINCIDE   |   **Gravedad si falla:** menor   |   **Magnitud:** `qc_kvar`
- **Entradas:** P_kW = 100.0, cos_phi_1 = 0.7, cos_phi_2 = 0.95
- **Fórmula y cuenta:** tan(acos 0,70) = 1.02020; tan(acos 0,95) = 0.32868; Qc = P*(tan phi1 - tan phi2) = 100*0.69152 = 69.1520 kvar
- **Valor esperado:** 69.152 kvar (tolerancia 0.01 %); fuente: `closed_form`
- **Llamada al motor:** `aea_reactive.reactiva_a_compensar` — p_kw, fp_actual=0.7, fp_objetivo=0.95
- **Resultado del motor:** 69.152
- **Diferencia:** -0.000 %
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Fórmula estándar de trigonometría; implementación.

### n2_reactiva_banco — Banco de capacitores en escalones comerciales para el Qc del caso n1 (400 V)

- **Estado:** COINCIDE   |   **Gravedad si falla:** menor   |   **Magnitud:** `instalado_kvar`
- **Entradas:** Qc_kvar = 69.152, U_V = 400, escalones_kvar = [5, 10, 12.5, 25, 50], N_min = 4
- **Fórmula y cuenta:** Regla de los datos del repo: escalón = mayor paso <= Qc/N_min = 69.152/4 = 17.288 -> 12.5 kvar; n = ceil(Qc/escalón) = ceil(5.532) = 6; instalado = 6*12.5 = 75.0 kvar; corriente = 75.0e3/(sqrt(3)*400) = 108.25 A; de diseño x1.43 = 154.80 A
- **Valor esperado:** 75 kvar (tolerancia 0.01 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_tables.json#/constantes/compensacion_reactiva/pasos_kvar`
- **Llamada al motor:** `aea_reactive.banco` — q_kvar=Qc, u_v=400
- **Resultado del motor:** 75
- **Diferencia:** +0.000 %
- **Detalle del motor:** banco = {'escalon_kvar': 12.5, 'escalones': 6, 'instalado_kvar': 75.0, 'corriente_a': 108.25, 'corriente_diseno_a': 154.8}
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. El resultado sobrepasa Qc (más capacitores que lo necesario). La regla de elección del escalón es del motor.

### o1_rayos_area — Superficie de captación 20 x 10 x 8 m

- **Estado:** COINCIDE   |   **Gravedad si falla:** menor   |   **Magnitud:** `ad_m2`
- **Entradas:** L_m = 20.0, W_m = 10.0, H_m = 8.0
- **Fórmula y cuenta:** Ad = L*W + 6H(L+W) + 9*pi*H^2 = 200 + 6*8*30 + 9*pi*64 = 200 + 1440 + 1809.557 = 3449.557 m2
- **Valor esperado:** 3449.56 m2 (tolerancia 0.01 %); fuente: `closed_form`
- **Llamada al motor:** `aea_lightning.superficie_captacion_m2` — largo_m, ancho_m, altura_m
- **Resultado del motor:** 3449.56
- **Diferencia:** +0.000 %
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Geometría del área equivalente de captación (talud 1:3); la forma de la fórmula es la del motor.

### o2_rayos_nd — Impactos directos anuales, Ng 2, estructura aislada

- **Estado:** COINCIDE   |   **Gravedad si falla:** menor   |   **Magnitud:** `nd_por_anio`
- **Entradas:** Ng_km2_anio = 2.0, Ad_m2 = 3449.5574, Cd = 1.0
- **Fórmula y cuenta:** Nd = Ng*Ad*Cd*1e-6 = 2.0*3449.557*1.0*1e-6 = 6.899115e-03 por año (Cd = 1.0 de entorno_cd.aislada en los datos del repo)
- **Valor esperado:** 0.00689911 1/año (tolerancia 0.01 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_tables.json#/constantes/descargas_atmosfericas/entorno_cd/aislada`
- **Llamada al motor:** `aea_lightning.impactos_directos_anuales` — ng=2, ad_m2=Ad, entorno='aislada'
- **Resultado del motor:** 0.00689911
- **Diferencia:** +0.000 %
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Los valores de Cd son 'típicos, a revisar' según el propio módulo.

### p1_sobrecarga_mcb16_iz20 — Coordinación de sobrecarga: MCB 16 A con Iz = 20 A

- **Estado:** COINCIDE   |   **Gravedad si falla:** seguridad   |   **Magnitud:** `i2_sobre_1_45_iz`
- **Entradas:** Ib_A = 14, In_A = 16, Iz_A = 20, tipo = "mcb"
- **Fórmula y cuenta:** I2 = k2*In = 1.45*16 = 23.2 A; límite = 1.45*Iz = 1.45*20 = 29.0 A; cociente I2/(1,45 Iz) = 0.800 (<= 1 cumple); In <= Iz (16 <= 20) cumple
- **Valor esperado:** 0.8 - (tolerancia 0.01 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_tables.json#/constantes/proteccion_k2_convencional/mcb`
- **Llamada al motor:** `aea_conductors.verify_overload` — i_b_a=14, i_n_a=16, i_z_a=20, i_2_a=aea_protection.i2_convencional(16,'mcb'); cociente = i_2/(policy.k_max_i2_iz()*i_z)
- **Resultado del motor:** 0.8
- **Diferencia:** -0.000 %
- **Detalle del motor:** I2 = 23.20 A; verify_overload = {'ib_le_in': True, 'in_le_iz': True, 'i2_le_1_45_iz': True, 'cumple': True}
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Camino directo de verificación. El veredicto 'cumple' también se informa.

### p2_pipeline_no_evalua_i2 — El pipeline no evalúa I2 <= 1,45 Iz (información)

- **Estado:** SIN VALOR OFICIAL   |   **Gravedad si falla:** menor   |   **Magnitud:** `i2_en_resultado_del_pipeline`
- **Entradas:** circuito = "una carga de 14 A, trifásica, 10 m"
- **Fórmula y cuenta:** Se ejecuta aea_pipeline.calculate con un circuito y se miran las claves del detalle: el pipeline elige la sección por Iz >= In y caída de tensión; no guarda ni calcula I2. Para MCB (k2 = 1,45) y MCCB (1,30) la condición I2 <= 1,45 Iz se deduce de In <= Iz, así que hoy no cambia resultados; con un fusible gG (k2 = 1,60) sí podría fallar con In = Iz. La memoria de tablero (board_memo) sí calcula coordinacion_ok.
- **Valor esperado:** ninguno (decisión del dueño)
- **Llamada al motor:** `aea_pipeline.calculate` — tablero 380 V / 10 kA, un circuito; busca claves i2 en el detalle
- **Resultado del motor:** False
- **Diferencia:** -
- **Detalle del motor:** claves del detalle del pipeline: ['aislacion', 'cadena', 'cumple', 'du_acum_pct', 'du_propia_pct', 'fases', 'fp', 'ib_a', 'icc_min_a', 'in_a', 'instalacion', 'iz_a', 'kind', 'largo_m', 'limite_pct', 'material', 'metodo', 'neutro_mm2', 'p_kw', 'padre', 'pe_mm2', 'ruta', 'ruta_limitante', 's_termica_mm2', 'seccion_min_mm2', 'solucion', 'tipo', 'topologia']; claves con I2/coordinación: ninguna; In = 16 A, Iz = 18.0 A, S = 2.5 mm2
- **Qué significa:** No hay valor esperado: solo el texto oficial o una decisión del dueño lo fija. Se muestra qué hace hoy el motor. Informativo: no es un defecto mientras solo existan MCB y MCCB en el pipeline. Decisión del dueño si se incorporan fusibles.

### q1_corriente_cabecera_tablero — Corriente de cabecera del tablero: suma aritmética vs ponderada por demanda

- **Estado:** SIN VALOR OFICIAL   |   **Gravedad si falla:** importante   |   **Magnitud:** `ib_cabecera_a`
- **Entradas:** circuitos_Ib_A = [10, 20, 30], factor_demanda = 0.8, origen_factor = "aea_demand.coef_simultaneity_770(3 circuitos) = 0,8, solo ilustrativo"
- **Fórmula y cuenta:** Suma aritmética = 10+20+30 = 60 A; ponderada = 0,8*60 = 48 A. Si la cabecera debe llevar la demanda o la suma de las corrientes de proyecto es una decisión de criterio (la plataforma fija los factores de demanda del sistema en 1,0 hasta que el proyecto fije otro).
- **Valor esperado:** ninguno (decisión del dueño)
- **Llamada al motor:** `board_feeders.head_current` — pipeline.calculate sobre 3 circuitos; board_feeders.head_current(datos, detalle)
- **Resultado del motor:** 60
- **Diferencia:** -
- **Detalle del motor:** head_current (suma aritmética) = 60.0 A; ponderada con coef 770 de 3 circuitos (0.8) = 48.00 A; el cable de acometida se dimensiona con la suma
- **Qué significa:** No hay valor esperado: solo el texto oficial o una decisión del dueño lo fija. Se muestra qué hace hoy el motor. Hoy el cable de acometida se dimensiona con la suma aritmética (conservador, sobredimensiona). Decisión del dueño.

### r1_tomas_dormitorio_8m2 — Tomacorrientes de un dormitorio de 8 m2

- **Estado:** COINCIDE   |   **Gravedad si falla:** menor   |   **Magnitud:** `bocas_requeridas`
- **Entradas:** uso = "bedroom", largo_m = 2.5, ancho_m = 3.2, area_m2 = 8.0
- **Fórmula y cuenta:** Texto fuente del propio motor: «AEA 90364-7-771 (2006), Tabla 771.8.III (viviendas): tres bocas de 10 a 36 m² (dos si es menor de 10 m²)». 8 m2 < 10 m2 -> 2 bocas. El motor define el dormitorio como 'fixed' con min = 3.
- **Valor esperado:** 2 bocas (tolerancia 0.01 %); fuente: `repo_data:harness/src/engines/calculation/receptacles/src/epc_receptacles/data/uses.json#/uses/bedroom/source`
- **Llamada al motor:** `epc_receptacles.run` — documento con un local: use, length_m, width_m, receptacle='tug'; lee rooms[0].required
- **Resultado del motor:** 2
- **Diferencia:** +0.000 %
- **Detalle del motor:** motor: a fixed number for this use, at least 2 (confianza 0.9)
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. El motor ignora la excepción de menos de 10 m2 que su propio texto fuente menciona. El valor esperado se toma de ese texto (repo_data), no de memoria.

### r2_tomas_dormitorio_12m2 — Tomacorrientes de un dormitorio de 12 m2

- **Estado:** COINCIDE   |   **Gravedad si falla:** menor   |   **Magnitud:** `bocas_requeridas`
- **Entradas:** uso = "bedroom", largo_m = 3.0, ancho_m = 4.0, area_m2 = 12.0
- **Fórmula y cuenta:** Texto fuente del propio motor: «AEA 90364-7-771 (2006), Tabla 771.8.III (viviendas): tres bocas de 10 a 36 m² (dos si es menor de 10 m²)». 12 m2 está entre 10 y 36 m2 -> 3 bocas.
- **Valor esperado:** 3 bocas (tolerancia 0.01 %); fuente: `repo_data:harness/src/engines/calculation/receptacles/src/epc_receptacles/data/uses.json#/uses/bedroom/source`
- **Llamada al motor:** `epc_receptacles.run` — documento con un local: use, length_m, width_m, receptacle='tug'; lee rooms[0].required
- **Resultado del motor:** 3
- **Diferencia:** +0.000 %
- **Detalle del motor:** motor: a fixed number for this use, at least 3 (confianza 0.9)
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Control: debe coincidir.

### r3_tomas_estar_20m2 — Tomacorrientes de una sala de estar de 20 m2

- **Estado:** COINCIDE   |   **Gravedad si falla:** menor   |   **Magnitud:** `bocas_requeridas`
- **Entradas:** uso = "living", largo_m = 4.0, ancho_m = 5.0, area_m2 = 20.0
- **Fórmula y cuenta:** Texto fuente: «AEA 90364-7-771 (2006), Tabla 771.8.III (viviendas): una boca cada 6 m² o fracción, mínimo dos». ceil(20/6) = ceil(3,33) = 4 bocas (mínimo 2).
- **Valor esperado:** 4 bocas (tolerancia 0.01 %); fuente: `repo_data:harness/src/engines/calculation/receptacles/src/epc_receptacles/data/uses.json#/uses/living/source`
- **Llamada al motor:** `epc_receptacles.run` — documento con un local: use, length_m, width_m, receptacle='tug'; lee rooms[0].required
- **Resultado del motor:** 4
- **Diferencia:** +0.000 %
- **Detalle del motor:** motor: one outlet per 6 m² of 20.0 m², at least 2 (confianza 0.9)
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Control: debe coincidir.

### r4_tomas_pasillo — Tomacorrientes de un pasillo de 10 m x 1,2 m

- **Estado:** SIN VALOR OFICIAL   |   **Gravedad si falla:** menor   |   **Magnitud:** `bocas_requeridas`
- **Entradas:** uso = "corridor", largo_m = 10.0, ancho_m = 1.2, area_m2 = 12.0
- **Fórmula y cuenta:** Texto fuente: «AEA 90364-7-771 (2006), Tabla 771.8.VI (oficinas y locales) y AEA 90364-7-771 (2006), Tabla 771.8.III (viviendas): una boca cada 5 m de longitud o fracción (en un pasillo angosto, una cada 10 m de perímetro)». Por longitud: ceil(10/5) = 2 bocas; por perímetro (22,4 m, 'angosto'): ceil(22,4/10) = 3 bocas. El motor usa perímetro/10 para todo pasillo. Qué se considera 'angosto' lo decide el texto oficial.
- **Valor esperado:** ninguno (valor oficial pendiente)
- **Llamada al motor:** `epc_receptacles.run` — documento con un local: use, length_m, width_m, receptacle='tug'; lee rooms[0].required
- **Resultado del motor:** 2
- **Diferencia:** -
- **Detalle del motor:** motor: one outlet per 5 m of a length of 10.0 m, at least 1 (confianza 0.9)
- **Qué significa:** No hay valor esperado: solo el texto oficial o una decisión del dueño lo fija. Se muestra qué hace hoy el motor. El motor aplica la regla del pasillo angosto a cualquier pasillo.

### s1_pe_1_5mm2_conductors — Sección del PE para fase de 1,5 mm2 (aea_conductors.pe_section)

- **Estado:** COINCIDE   |   **Gravedad si falla:** importante   |   **Magnitud:** `s_pe_mm2`
- **Entradas:** S_fase_mm2 = 1.5
- **Fórmula y cuenta:** Regla de la sección del PE: S <= 16 -> S = 1,5 mm2; mínimo del PE en los datos del repo = 2,5 mm2 (771.13.I, clave pe) -> PE = max(1,5; 2,5) = 2,5 mm2
- **Valor esperado:** 2.5 mm2 (tolerancia 0.01 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_tables.json#/constantes/771.13.I_secciones_minimas_mm2/pe`
- **Llamada al motor:** `aea_conductors.pe_section` — seccion_mm2 / s_fase_mm2 = 1.5
- **Resultado del motor:** 2.5
- **Diferencia:** +0.000 %
- **Detalle del motor:** aea_conductors.pe_section = 2.5; aea_earthing.seccion_pe_mm2 = 2.5
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. aea_conductors.pe_section aplica el mínimo de 2,5; aea_earthing.seccion_pe_mm2 no. Dos funciones para el mismo dato.

### s1_pe_1_5mm2_earthing — Sección del PE para fase de 1,5 mm2 (aea_earthing.seccion_pe_mm2)

- **Estado:** COINCIDE   |   **Gravedad si falla:** importante   |   **Magnitud:** `s_pe_mm2`
- **Entradas:** S_fase_mm2 = 1.5
- **Fórmula y cuenta:** Regla de la sección del PE: S <= 16 -> S = 1,5 mm2; mínimo del PE en los datos del repo = 2,5 mm2 (771.13.I, clave pe) -> PE = max(1,5; 2,5) = 2,5 mm2
- **Valor esperado:** 2.5 mm2 (tolerancia 0.01 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_tables.json#/constantes/771.13.I_secciones_minimas_mm2/pe`
- **Llamada al motor:** `aea_earthing.seccion_pe_mm2` — seccion_mm2 / s_fase_mm2 = 1.5
- **Resultado del motor:** 2.5
- **Diferencia:** +0.000 %
- **Detalle del motor:** aea_conductors.pe_section = 2.5; aea_earthing.seccion_pe_mm2 = 2.5
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. aea_conductors.pe_section aplica el mínimo de 2,5; aea_earthing.seccion_pe_mm2 no. Dos funciones para el mismo dato.

### s2_pe_95mm2 — Sección del PE para fase de 95 mm2: valor no comercial

- **Estado:** SIN VALOR OFICIAL   |   **Gravedad si falla:** menor   |   **Magnitud:** `s_pe_mm2`
- **Entradas:** S_fase_mm2 = 95
- **Fórmula y cuenta:** S > 35 -> S/2 = 47,5 mm2, que no es sección comercial. Si el PE debe redondearse hacia arriba a la serie (50 mm2) es decisión del texto oficial (el neutro sí se redondea a la serie en el motor).
- **Valor esperado:** ninguno (valor oficial pendiente)
- **Llamada al motor:** `aea_conductors.pe_section` — seccion_mm2 = 95
- **Resultado del motor:** 50
- **Diferencia:** -
- **Detalle del motor:** aea_conductors.pe_section = 50; aea_earthing.seccion_pe_mm2 = 50
- **Qué significa:** No hay valor esperado: solo el texto oficial o una decisión del dueño lo fija. Se muestra qué hace hoy el motor. Ambas funciones devuelven 47,5.

### t1_aislacion_por_defecto — Aislación por defecto sin criterios de diseño

- **Estado:** DIFIERE   |   **Gravedad si falla:** importante   |   **Magnitud:** `aislacion`
- **Entradas:** criterios = null
- **Fórmula y cuenta:** El archivo de criterios de diseño del repo (data/design-criteria.json, criterio insulation) propone por defecto XLPE. El pipeline sin criterios resuelve la aislación por su propio texto por defecto.
- **Valor esperado:** xlpe  (tolerancia 0 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/data/design-criteria.json#/criteria/9/default`
- **Llamada al motor:** `aea_pipeline.resolver_criterios` — resolver_criterios(None)[3]
- **Resultado del motor:** pvc
- **Diferencia:** -
- **Detalle del motor:** resolver_criterios(None) -> aislación 'pvc', material 'cu'; resolver_criterios({}) -> 'pvc'
- **Qué significa:** El motor se aparta del valor de referencia más que la tolerancia. Hay que decidir si el defecto está en el motor o en el criterio del caso. Si el pipeline se usa sin pasar criterios, dimensiona con PVC mientras el dato del repo dice XLPE: dos defaults distintos para el mismo dato. Con criterios explícitos no hay problema.

### t2_aislacion_efecto_seccion — Efecto del default de aislación en la sección elegida (informativo)

- **Estado:** SIN VALOR OFICIAL   |   **Gravedad si falla:** menor   |   **Magnitud:** `seccion_mm2_sin_criterios`
- **Entradas:** circuito = "30 A trifásico, 40 m", con_criterios = {"insulation": "XLPE"}
- **Fórmula y cuenta:** Se calcula el mismo circuito sin criterios y con criterios {insulation: XLPE} y se informa la sección y la Iz de cada uno. No hay valor esperado: depende de cuál sea el default correcto.
- **Valor esperado:** ninguno (decisión del dueño)
- **Llamada al motor:** `aea_pipeline.calculate` — dos corridas de calculate, con y sin criterios
- **Resultado del motor:** None
- **Diferencia:** -
- **Detalle del motor:** criterios=None: S = 6 mm2, Iz = 32.0 A, aislación pvc, método B1, dU = 1.736 % | criterios={'insulation': 'XLPE'}: S = 6 mm2, Iz = 32.0 A, aislación pvc, método B1, dU = 1.736 %
- **Qué significa:** No hay valor esperado: solo el texto oficial o una decisión del dueño lo fija. Se muestra qué hace hoy el motor. Informativo.

### u1_c_min_consistencia — Factor c_min: constantes del motor vs dato del repo

- **Estado:** COINCIDE   |   **Gravedad si falla:** menor   |   **Magnitud:** `c_min`
- **Entradas:** fuentes = "short_circuit.C_MIN_BT, aea_pipeline.C_MIN_BT"
- **Fórmula y cuenta:** Dato del repo: c_tension_min = 0.95. Se compara con el de short_circuit.C_MIN_BT (el de aea_pipeline se informa).
- **Valor esperado:** 0.95 - (tolerancia 0.01 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_tables.json#/constantes/impedancias_estandar/c_tension_min`
- **Llamada al motor:** `short_circuit.C_MIN_BT` — lee la constante
- **Resultado del motor:** 0.95
- **Diferencia:** +0.000 %
- **Detalle del motor:** aea_pipeline.C_MIN_BT = 0.95
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Un mismo valor en tres lugares (viola ADR-0012 si algún día divergen).

### u2_c_max_consistencia — Factor c_max: constantes del motor vs dato del repo

- **Estado:** COINCIDE   |   **Gravedad si falla:** menor   |   **Magnitud:** `c_max`
- **Entradas:** fuentes = "short_circuit.C_MAX_BT_TOL_6, aea_pipeline.C_MAX_BT"
- **Fórmula y cuenta:** Dato del repo: c_fuente_max = 1.05. Se compara con short_circuit.C_MAX_BT_TOL_6 (el de aea_pipeline se informa).
- **Valor esperado:** 1.05 - (tolerancia 0.01 %); fuente: `repo_data:harness/src/engines/calculation/aea90364/src/epc_aea90364/aea_tables.json#/constantes/impedancias_estandar/c_fuente_max`
- **Llamada al motor:** `short_circuit.C_MAX_BT_TOL_6` — lee la constante
- **Resultado del motor:** 1.05
- **Diferencia:** +0.000 %
- **Detalle del motor:** aea_pipeline.C_MAX_BT = 1.05
- **Qué significa:** El motor coincide con el valor de referencia dentro de la tolerancia. Idem u1.
