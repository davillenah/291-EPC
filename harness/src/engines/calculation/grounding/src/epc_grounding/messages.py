"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_current_kind": {
        "en": "current 'ca' (AC) or 'cc' (DC)",
        "es": "corriente 'ca' o 'cc'",
    },
    "err_empty_list": {
        "en": "empty list",
        "es": "lista vacía",
    },
    "err_no_dc_value": {
        "en": "no DC value in that range",
        "es": "sin valor cc en ese rango",
    },
    "err_ratio_range": {
        "en": "L/d is outside 25-3000",
        "es": "L/d fuera de 25–3000",
    },
    "err_scheme": {
        "en": "scheme 'TN' or 'TT'",
        "es": "esquema 'TN' o 'TT'",
    },
    "err_voltage_outside_table": {
        "en": "un_v is outside the table (<= 400 V)",
        "es": "un_v fuera de la tabla (≤ 400 V)",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
