# Dialogo 01 — Simulacion 04, taller industrial (datos ficticios, modo edit)
Daniel = usuario. Claude actua como orchestrator y electrical_lv; solo usa `epc` (CLI). Pedido del usuario: que el harness resuelva solo y pida lo minimo.

**Daniel:** Proyecto nuevo: taller industrial de 36 x 20 m, una planta, motores grandes, compensacion reactiva a 0,95 y puesta a tierra importante. Cliente Talleres Industriales del Sur S.A. No quiero elegir luminarias ni tableros.

**electrical_lv — Bloque 1 identificacion:** codigo, cliente y contacto, descripcion.
**Daniel:** 2026-ES-TAIN-0311; TALLERES INDUSTRIALES DEL SUR S.A. (ficticio), Gerente de Planta Ficticio; "Taller industrial".
**electrical_lv — Bloque 2 sitio:** direccion, pais, tipo.
**Daniel:** Parque Industrial Ficticio, Lote 12, Ciudad Ficticia, AR; taller industrial de una planta.
**electrical_lv — Bloque 3 suministro (D24):** origen y tension; esquema de tierra; Icc y origen.
**Daniel:** Red MT de la distribuidora ficticia, transformador propio de 630 kVA, medido en BT, 400 V. Esquema TN-S. Icc 18 kA informada por la distribuidora ficticia (nota de factibilidad ficticia).
**electrical_lv:** El formulario solo acepta TT, TN, IT. Registro TN (aviso: se pierde el dato "S"). Icc y origen registrados como declarados, no verificados.
**electrical_lv — Bloque 4:** criterios AEA 90364 / IRAM 2178; ingeniero responsable ficticio MAT-0000; idioma es.
**Daniel:** Confirmado.

**electrical_lv — cargas y estudios:** (no hay formulario guiado para esto; se completa a mano `loads.json` y `engine_inputs.json`)
Cargas: torno 15 kW, fresadora 11, compresor 30 (estrella-triangulo), puente grua 10, extractor 5,5, bomba 4, horno 24, soldadoras 16, clima oficina 5 (1F). Estudios pedidos: motores, reactiva (fp objetivo 0,95), bandejas/conductos, puesta a tierra (90 ohm.m, jabalina 3 m).
No se dan luminarias, tomas, alturas, luces objetivo, elevacion ni coordenadas de tableros: se quiere ver que resuelve el harness solo.
