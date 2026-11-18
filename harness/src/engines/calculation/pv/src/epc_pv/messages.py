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
    "gap_hours": {
        "en": "The weather file has {n} hours with the sun above the horizon and no irradiance.",
        "es": "El archivo de clima tiene {n} horas con el sol sobre el horizonte y sin irradiancia.",
    },
    "layout_no_fit": {
        "en": "The tables do not fit in the site: {n} table(s) were left out. Enlarge the site, raise the number of modules per table, or reduce the tilt.",
        "es": "Las mesas no entran en el predio: quedaron {n} mesa(s) afuera. Ampliar el predio, aumentar los módulos por mesa o reducir la inclinación.",
    },
    "layout_pad_tight": {
        "en": "{n} inverter(s) do not fit in the gap between rows (pad deeper than the gap): move them to the end of the row.",
        "es": "{n} inversor(es) no entran en el espacio entre filas (la base es más profunda que el espacio): moverlos al extremo de la fila.",
    },
    "err_json": {"en": "the input is not valid JSON: {detail}", "es": "la entrada no es un JSON válido: {detail}"},
    "err_missing": {"en": "{where} is missing: {names}", "es": "falta en {where}: {names}"},
    "err_type": {"en": "{name} must be {kind}", "es": "{name} debe ser {kind}"},
    "err_range": {"en": "{name} must be {rule} (got {value})", "es": "{name} debe ser {rule} (se recibió {value})"},
    "err_length": {
        "en": "weather.{name} has {n} values and the file has {expected} hours",
        "es": "weather.{name} tiene {n} valores y el archivo tiene {expected} horas",
    },
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
