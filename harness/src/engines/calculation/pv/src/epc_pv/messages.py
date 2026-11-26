"""Every text the user can see, in English (source) and Spanish. A message is a code with two templates; `{name}` are filled from the parameters."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "typical_values": {
        "en": "Typical values not yet confirmed by the owner: do not use the result to size or to sell a plant.",
        "es": "Valores típicos aún no confirmados por el dueño: no usar el resultado para dimensionar ni para vender una planta.",
    },
    "wind_proxy": {
        "en": "The temperature coefficient of the maximum-power voltage is taken equal to that of the open-circuit voltage.",
        "es": "El coeficiente de temperatura de la tensión de máxima potencia se toma igual al de la tensión de circuito abierto.",
    },
    "t_min_from_weather": {
        "en": "The design minimum temperature is the coldest hour of the weather file ({t_min_c} C); give `design_t_min_c` for a safer value.",
        "es": "La temperatura mínima de diseño es la hora más fría del archivo de clima ({t_min_c} C); indicar `design_t_min_c` para un valor más seguro.",
    },
    "err_no_series": {
        "en": "Array {array}: no string length keeps the cold open-circuit voltage under the inverter limit and the hot maximum-power voltage inside the MPPT window (allowed {s_min} to {s_max}).",
        "es": "Arreglo {array}: ninguna longitud de string mantiene la tensión de circuito abierto en frío bajo el límite del inversor y la de máxima potencia en caliente dentro de la ventana MPPT (permitido {s_min} a {s_max}).",
    },
    "err_series_fixed": {
        "en": "Array {array}: the given string length {n_series} is outside the allowed range {s_min} to {s_max}.",
        "es": "Arreglo {array}: la longitud de string indicada {n_series} está fuera del rango permitido {s_min} a {s_max}.",
    },
    "warn_current": {
        "en": "Array {array}: {strings} strings per MPPT input exceed the {limit} the inverter inputs allow; add inverters or inputs.",
        "es": "Arreglo {array}: {strings} strings por entrada MPPT superan los {limit} que admiten las entradas del inversor; agregar inversores o entradas.",
    },
    "shading_computed": {
        "en": "Array {array}: the shade is computed (far horizon and row to row, direct beam only): {loss} % of the yearly plane-of-array energy; the typical shading loss is not added.",
        "es": "Arreglo {array}: la sombra se calcula (horizonte lejano y fila a fila, solo haz directo): {loss} % de la energía anual en el plano del módulo; no se suma la pérdida típica de sombras.",
    },
    "err_tracker_shade": {
        "en": "Array {array}: a tracker array takes no `row_shading` or `near_obstacles` (backtracking handles the rows); remove them.",
        "es": "Arreglo {array}: un arreglo con seguidor no admite `row_shading` ni `near_obstacles` (el backtracking resuelve las filas); quitarlos.",
    },
    "gap_hours": {
        "en": "The weather file has {n} hours with the sun above the horizon and no irradiance.",
        "es": "El archivo de clima tiene {n} horas con el sol sobre el horizonte y sin irradiancia.",
    },
    "layout_no_fit": {
        "en": "The tables do not fit in the site: {n} table(s) were left out. Enlarge the site, raise the number of modules per table, or reduce the tilt.",
        "es": "Las mesas no entran en el predio: quedaron {n} mesa(s) afuera. Ampliar el predio, aumentar los módulos por mesa o reducir la inclinación.",
    },
    "roof_short": {
        "en": "The roof holds {capacity} modules and {n} more were asked: add planes, reduce the margin or ask for fewer modules.",
        "es": "El techo admite {capacity} módulos y se pidieron {n} más: agregar faldones, reducir el retiro o pedir menos módulos.",
    },
    "layout_pad_tight": {
        "en": "{n} inverter(s) do not fit in the gap between rows (pad deeper than the gap): move them to the end of the row.",
        "es": "{n} inversor(es) no entran en el espacio entre filas (la base es más profunda que el espacio): moverlos al extremo de la fila.",
    },
    "isc_not_checked": {
        "en": "Array {array}: the inverter data sheet gives no maximum short-circuit current per MPPT input, so only the operating input current limits the strings per input. Confirm the short-circuit limit with the manufacturer (pending review).",
        "es": "Arreglo {array}: la hoja de datos del inversor no da la corriente de cortocircuito máxima por entrada MPPT, por lo que solo la corriente de operación limita los strings por entrada. Confirmar el límite de cortocircuito con el fabricante (pendiente de revisión).",
    },
    "table_shrunk": {
        "en": "The table of {rows} x {per_row} modules does not fit the site; the harness uses {rows_fit} x {per_row_fit} (pending review). Give a table size in the advanced section to change it.",
        "es": "La mesa de {rows} x {per_row} módulos no entra en el predio; el harness usa {rows_fit} x {per_row_fit} (pendiente de revisión). Indicar el tamaño de mesa en la sección avanzada para cambiarlo.",
    },
    "module_auto": {
        "en": "Module {model} chosen from the catalog: it installs the most power on the structure ({n} modules, {kwp} kWp). Best alternatives: {table}. Give a module in the advanced section to fix it (pending review).",
        "es": "Módulo {model} elegido del catálogo: es el que más potencia instala en la estructura ({n} módulos, {kwp} kWp). Mejores alternativas: {table}. Indicar un módulo en la sección avanzada para fijarlo (pendiente de revisión).",
    },
    "inverter_auto": {
        "en": "Array {array}: inverter {model} chosen from the catalog ({n} unit(s) for {kwp} kWp at DC/AC {ratio}); give another inverter in the advanced section to change it (pending review).",
        "es": "Arreglo {array}: inversor {model} elegido del catálogo ({n} unidad(es) para {kwp} kWp con CC/CA {ratio}); indicar otro inversor en la sección avanzada para cambiarlo (pendiente de revisión).",
    },
    "inverters_raised": {
        "en": "Array {array}: {before} inverter(s) would give the requested DC/AC ratio, but the input current of the MPPT inputs allows fewer strings per input, so {after} are installed (real DC/AC {ratio}). A data sheet with the short-circuit limit, or another inverter, can lower the count (pending review).",
        "es": "Arreglo {array}: {before} inversor(es) darían la relación CC/CA pedida, pero la corriente de entrada de los MPPT admite menos strings por entrada, por lo que se instalan {after} (CC/CA real {ratio}). Una hoja de datos con el límite de cortocircuito, u otro inversor, puede bajar la cantidad (pendiente de revisión).",
    },
    "roof_dxf_azimuth": {
        "en": "Roof plane {plane}: the drawing gives no azimuth; the harness chooses it (the plane is only a placement area).",
        "es": "Faldón {plane}: el dibujo no indica el azimut; lo elige el harness (el faldón es solo un área de colocación).",
    },
    "roof_dxf_tilt": {
        "en": "Roof plane {plane}: the drawing gives no tilt; the harness chooses it and the plan extent is used as the slope length.",
        "es": "Faldón {plane}: el dibujo no indica la inclinación; la elige el harness y la extensión en planta se usa como largo del faldón.",
    },
    "roof_dxf_obstacles": {
        "en": "{n} obstacle(s) of the roof drawing are not inside any roof plane and were ignored.",
        "es": "{n} obstáculo(s) del dibujo de cubierta no están dentro de ningún faldón y se ignoraron.",
    },
    "foundation_depth_not_found": {
        "en": "Structure {structure}: its record gives no embedment depth, so nothing is drawn below the surface; the engineer of record sets the foundation (pile or screw length, footing).",
        "es": "Estructura {structure}: su registro no da la profundidad de empotramiento, por lo que no se dibuja nada bajo la superficie; el ingeniero de registro define la fundación (largo de pilote o tornillo, zapata).",
    },
    "foundation_unverified": {
        "en": "Structure {structure}: foundation data is {status} (pending review); the embedment drawn is reference geometry, not a geotechnical or structural design.",
        "es": "Estructura {structure}: los datos de fundación están {status} (pendientes de revisión); el empotramiento dibujado es geometría de referencia, no un diseño geotécnico ni estructural.",
    },
    "roof_wind_pending": {
        "en": "Wind uplift, ballast, roof loads and fixings are not calculated: they need the structure data of the roof and the wind code, and no wind value is recorded in the norm register.",
        "es": "No se calculan la succión del viento, el lastre, las cargas del techo ni las fijaciones: requieren los datos de la estructura del techo y la norma de viento, y no hay ningún valor de viento en el registro de normas.",
    },
    "err_dxf": {"en": "roof DXF: {detail}", "es": "DXF de cubierta: {detail}"},
    "err_json": {"en": "the input is not valid JSON: {detail}", "es": "la entrada no es un JSON válido: {detail}"},
    "err_missing": {"en": "{where} is missing: {names}", "es": "falta en {where}: {names}"},
    "err_type": {"en": "{name} must be {kind}", "es": "{name} debe ser {kind}"},
    "err_range": {"en": "{name} must be {rule} (got {value})", "es": "{name} debe ser {rule} (se recibió {value})"},
    "err_length": {
        "en": "weather.{name} has {n} values and the file has {expected} hours",
        "es": "weather.{name} tiene {n} valores y el archivo tiene {expected} horas",
    },
    "err_pvgis_http": {"en": "PVGIS did not answer: {detail}", "es": "PVGIS no respondió: {detail}"},
    "err_pvgis_payload": {"en": "the PVGIS answer is not the expected one: {detail}", "es": "la respuesta de PVGIS no es la esperada: {detail}"},
    "err_pvgis_shape": {"en": "the PVGIS typical year has {n} hours and {expected} consecutive hours are needed", "es": "el año típico de PVGIS tiene {n} horas y se necesitan {expected} horas consecutivas"},
    "err_choice": {"en": "{name} must be one of {choices} (got {value!r})", "es": "{name} debe ser uno de {choices} (se recibió {value!r})"},
}

LABELS: Dict[str, Dict[str, str]] = {
    "dc_kwh": {"en": "DC energy after losses (kWh)", "es": "Energía en continua tras pérdidas (kWh)"},
    "ac_kwh": {"en": "AC energy delivered (kWh)", "es": "Energía en alterna entregada (kWh)"},
    "specific_yield_kwh_kwp": {"en": "Specific yield (kWh per kWp)", "es": "Rendimiento específico (kWh por kWp)"},
    "performance_ratio": {"en": "Performance ratio", "es": "Performance ratio"},
    "capacity_factor": {"en": "Capacity factor (AC)", "es": "Factor de capacidad (alterna)"},
    "poa_kwh_m2": {"en": "Plane-of-array irradiation (kWh/m2)", "es": "Irradiación en el plano del arreglo (kWh/m2)"},
    "clipping_kwh": {"en": "Energy lost by inverter clipping (kWh)", "es": "Energía perdida por recorte del inversor (kWh)"},
    "peak_ac_kw": {"en": "Peak AC power (kW)", "es": "Potencia pico en alterna (kW)"},
    "monthly_ac_kwh": {"en": "Monthly AC energy (kWh)", "es": "Energía mensual en alterna (kWh)"},
    "modules": {"en": "Modules", "es": "Módulos"},
    "dc_kwp": {"en": "DC power at STC (kWp)", "es": "Potencia en continua en STC (kWp)"},
    "dc_ac_ratio": {"en": "DC to AC ratio", "es": "Relación continua a alterna"},
    "strings": {"en": "String layout", "es": "Configuración de strings"},
}


def bi(en: str, es: str) -> Dict[str, str]:
    """A parameter that is itself text in both languages."""
    return {"en": en, "es": es}


def _pick(params: Dict, lang: str) -> Dict:
    return {k: (v[lang] if isinstance(v, dict) and set(v) == {"en", "es"} else v) for k, v in params.items()}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages, with its parameters filled in (a parameter made with `bi` is taken in the language of the text)."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**_pick(params, lang)) for lang in ("en", "es")}


def item(code: str, **params) -> Dict[str, str]:
    """A warning item: the code and both texts."""
    return {"code": code, **text(code, **params)}
