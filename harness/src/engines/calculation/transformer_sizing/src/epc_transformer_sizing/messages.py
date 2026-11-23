"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_above_largest_rating": {
        "en": "required {required_kva:g} kVA exceeds the largest rating ({largest:g} kVA): {note}",
        "es": "la potencia requerida {required_kva:g} kVA supera la mayor potencia normalizada ({largest:g} kVA): {note}",
    },
    "err_not_finite_number": {
        "en": "{name} must be a finite number (got {value!r})",
        "es": "{name} debe ser un número finito (recibido {value!r})",
    },
    "err_out_of_range": {
        "en": "{name} must be {relation} {minimum} (got {got})",
        "es": "{name} debe ser {relation} {minimum} (recibido {got})",
    },
    "err_reserve_required": {
        "en": "reserve_pct is required: no default growth/reserve criterion has been decided; provide it explicitly",
        "es": "falta reserve_pct: no se decidió un criterio de crecimiento o reserva por defecto; indicarlo explícitamente",
    },
    "err_series_empty": {
        "en": "the rating series is empty",
        "es": "la serie de potencias normalizadas está vacía",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
