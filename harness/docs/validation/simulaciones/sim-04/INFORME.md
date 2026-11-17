# Simulación 04 — Taller industrial (ficticio)

Cuarto proyecto de simulación. Nave de 36 x 20 m, una planta, 8 ambientes, 6 motores (hasta 30 kW), horno, soldadoras y clima; TN, 18 kA, 400 V, transformador propio de 630 kVA; compensación reactiva a fp 0,95 y puesta a tierra con resistividad 90 ohm.m. Hecho solo con `epc` (init, run, review, submit, approve, issue) en modo `edit`, datos ficticios, proyecto fuera del repo, firma simulada `ing-simulado`. No se arregló nada del harness; todo lo hallado está en `BUGS-Y-TEMPORALES.md`. Base: rama `claude/project-thread-birb0y` (commit e944ff6).

## Resultado (verificado)
- 12 etapas ok; corrida completa 11,6 s; 34 archivos por transmittal. TR-002 (R1) `issued`, firmante `ing-simulado`, manifiesto con estado y firma.
- Salidas: unifilar y tablero (DXF), planos de iluminación y eléctrico (DXF, con lámina), 13 documentos en PDF y DOCX, XLSX de tablas, transmittal.
- Se confirman arreglos anteriores: bloqueo de `approve` con hallazgos major (3, diferencial) y la opción `--accept-major`; manifiesto y transmittal con estado `issued`; rótulo del unifilar con cliente; nomenclatura `AAAA-PROV-CLI-COD-E-LV-TIPO-NNN`; una sola convención de capas `A-*` / `E-*`; el cambio de un archivo de `inputs/` tras el alta se detecta ("1 input file(s) changed since intake").

## Punto pedido: estudios de motores, reactiva y tierra (verificado)
Se calculan y NO se documentan. El resultado está en `.epc/ssot/stage_06_cable_sizing.json`: arranque de los 6 motores (por ejemplo M-001: 152,8 A, caída 3,27 %; M-003 en estrella-triángulo 0,16 %), protección térmica y magnética; reactiva: fp 0,848, 37,5 kvar a compensar, banco de 40 kvar en 8 escalones de 5; tierra: una jabalina = 30,1 ohm. Ninguno de los 12 PDF, el XLSX, el unifilar ni el plano trae esos valores (búsqueda de kvar, jabalina, resistividad, arranque: sin resultados útiles). Del estudio solo queda un hallazgo "nota" por estudio. Tampoco hay veredicto de la resistencia de tierra (las funciones `ra_maxima` y `verifica_ra` se llaman, pero su resultado no sale).

## Datos que el harness pidió de más (pedido: que no pregunte)
1. Una luminaria declarada y la longitud de planta; con `main_board` la longitud se prohíbe y `elevation_m` pasa a ser obligatorio (dos mensajes distintos, uno por corrida).
2. Actividad, altura y luminaria para "Nave de producción": el catálogo no tiene ninguna actividad industrial.
3. Coordenadas del tablero general (a mano, en metros).
4. `kind: rcbo` en 3 circuitos para quitar los hallazgos de diferencial.
5. Cambiar `TN-S` por `TN`; escribir el cliente con guiones bajos.
6. Un JSON de "correcciones" con identificadores de hallazgo inventados para poder volver a correr, aunque el cambio no respondía a un hallazgo.

Datos que sí corresponde pedir: Icc y esquema de tierra (D24), resistividad, factor de potencia objetivo.
Sin esos datos, la primera corrida (sin `building`) terminó "ok" con solo 2 archivos y sin ningún documento ni aviso.

## Lo más importante que falló
- La nave de producción (la sala más grande, 353 m²) no se reconoce si el dibujo tiene portón ancho y ventanas (leyó 7 de 8); el proyecto la habría dejado sin luz ni circuitos sin avisar.
- Sin vía soportada para corregir un plano ya ingresado: el proyecto queda en `running` y hubo que crearlo de nuevo.
- Los motores, que son la carga principal, no están en el plano eléctrico; solo aparecen luminarias.
- Textos en inglés dentro de documentos en español y encabezados rotos en el estudio de cortocircuito.

## Supuestos (no verificados)
- Que el banco de 40 kvar y el arranque deberían ir en un documento propio o en la memoria de cálculo.
- Que el transformador de 630 kVA debería usarse (la etapa 4 dice "no hay entradas `transformer`").
- Tiempos de un contenedor de Claude, no de tu PC.

Archivos: `dibujar_taller.py` (temporal T-01) y `dialogo_01_inicio_proyecto.md`. El proyecto completo está en `pruebas-limite/simulacion-04/EPC-simulacion-04.tgz` de la carpeta del proyecto.
