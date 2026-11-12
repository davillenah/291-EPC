# De dónde sale cada valor de norma y qué falta conseguir

Actualizado el 2026-11-09. Un valor **sustentado** sale de una norma que está en el repositorio (`local/dev-knowledge/standards/`) y lleva su cláusula; sigue figurando como pendiente en la página de normas hasta que el dueño lo apruebe. Un valor **típico** no tiene fuente en el repositorio: se usa para calcular, el resultado lo avisa, y en la lista de abajo está la norma que hay que conseguir para reemplazarlo.

## Valores sustentados por una norma del repositorio

| Valor | Dónde está | Norma y cláusula |
|---|---|---|
| Conductor de equipotencialidad principal: la mitad del PE mayor, mínimo 6 mm² (Cu), máximo 25 mm² | constante `equipotencialidad_principal` | AEA 90364-5-54 (2006), 544.1.1 |
| Caída máxima en el arranque de motores: 15 % (5 % en régimen); cos φ de arranque 0,30 | constante `fuerza_motriz` y tabla de GDC | AEA 90364-7-770 (2017), 770.15.6; AEA 90364-5-52 (2006), 525 |
| Demanda por tipo de carga: la norma no da un factor por tipo, da potencias mínimas por circuito y coeficientes de simultaneidad por grado de electrificación (1; 0,9; 0,8; 0,7). Por eso el factor por tipo vale 1,0 | constante `factores_demanda_sistema` y `aea_demand` | AEA 90364-7-771 (2006), 771.9.1, 771.9.2, Tablas 771.9.I y 771.9.II |
| Tomacorrientes de oficinas y locales: salón general una boca cada 9 m² (mínimo dos), sala de reuniones, despacho privado (dos), recepción (una cada 18 m²), pasillo (una cada 5 m) | `epc_receptacles/data/uses.json` | AEA 90364-7-771 (2006), Tabla 771.8.VI |
| Tomacorrientes de viviendas: sala de estar (una cada 6 m², mínimo dos), dormitorio (tres), cocina (tres bocas más dos tomacorrientes), baño (una) | `epc_receptacles/data/uses.json` | AEA 90364-7-771 (2006), Tabla 771.8.III |
| Depósito: una boca de uso general cada 9 m de perímetro, mínimo dos | `uses.json` | AEA 90364-7-771 (2006), 771.8.3.3.3 |
| Transferencia con dispositivos tetrapolares; neutro del grupo con toma de tierra de 10 Ω o menos, separada de la de la red | estudio de grupo electrógeno y UPS | AEA 90364-7-771 (2006), 771-D.8 |
| Resistencia de puesta a tierra: 40 Ω (TT), tiempos de desconexión | reglas de la página de normas | AEA 90364-5-54 (2006), 541.3 y la parte 4 |
| Método de cortocircuito con c = 1,05 (máximo) | `short_circuit` | AEA 90364-7-771 (2006), Anexo 771-H |

## Valores típicos: falta conseguir la norma

| Qué es | Dónde está | Norma o fuente que falta |
|---|---|---|
| Frecuencia base de descargas, factores del entorno, de la estructura, del contenido, de la ocupación y de las consecuencias, y parámetros por nivel de protección (esfera, malla, bajadas) | constante `descargas_atmosfericas`, `aea_lightning` | IEC 62305-2 y 62305-3, IRAM 2184 |
| Carga térmica de climatización: irradiancia por orientación, calor de las personas, infiltración, aire exterior por uso, COP | `epc_hvac/data/typical.json` | ASHRAE Fundamentals (carga de refrigeración) y ASHRAE 62.1 (ventilación) |
| Protección del motor: clase de disparo, rangos comerciales del relé térmico, múltiplo del magnético | constante `fuerza_motriz` | IEC 60947-4-1 y catálogos de fabricantes |
| Grupo electrógeno y UPS: múltiplos de arranque, carga máxima, potencias comerciales, reserva y rendimientos | constante `respaldo_grupo_ups` | ISO 8528, IEC 62040 y AEA 90364-5-56 (servicios de seguridad) |
| Compensación de reactiva: pasos comerciales, factor de corriente del condensador, factor de potencia objetivo | constante `compensacion_reactiva` | IEC 60831 y el reglamento de la distribuidora |
| Resistencias a 20 °C por sección, reactancia típica y relación del aluminio | constante `impedancias_estandar` | IEC 60228 e IRAM 2022 |
| Resistencia de una malla de tierra (fórmula de Sverak) | `aea_earthing.resistencia_malla` | IEEE 80 |
| Valores `[VERIFICAR]` del cortocircuito en detalle (factores de impedancia, temperaturas) | `short_circuit.py` | AEA 90909-1 (está en el repositorio pero es un escaneo sin texto: hay que leerlo página por página) |

Las partes 2, 4, 4-42, 5 y la 90909-1 de la AEA están como escaneos sin texto; sus valores ya se extrajeron por lectura visual a las reglas de `harness/src/engines/calculation/aea90364/src/epc_aea90364/rules/` con su cláusula y página.
