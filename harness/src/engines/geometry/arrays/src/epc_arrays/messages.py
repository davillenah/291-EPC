"""Every error of the engine, in English (source) and Spanish. A message is a code with two templates (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_not_number": {
        "en": "{name} must be a finite number (got {value!r})",
        "es": "{name} debe ser un número finito (recibido {value!r})",
    },
    "err_not_point": {
        "en": "{name} must be a point [x, y] of two finite numbers (got {value!r})",
        "es": "{name} debe ser un punto [x, y] de dos números finitos (recibido {value!r})",
    },
    "err_not_count": {
        "en": "{name} must be a whole number of at least {low} (got {value!r})",
        "es": "{name} debe ser un entero de al menos {low} (recibido {value!r})",
    },
    "err_too_many": {
        "en": "the array would have {count} items, more than the limit {limit}",
        "es": "la matriz tendría {count} elementos, más que el límite {limit}",
    },
    "err_zero_spacing": {
        "en": "{name} must not be zero when there is more than one {what}",
        "es": "{name} no debe ser cero cuando hay más de un/a {what}",
    },
    "err_fill_zero": {
        "en": "the fill angle must not be zero",
        "es": "el ángulo de relleno no debe ser cero",
    },
    "err_fill_range": {
        "en": "the fill angle must be from -360 to 360 degrees (got {value:g})",
        "es": "el ángulo de relleno debe estar entre -360 y 360 grados (recibido {value:g})",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
