"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_circuit_not_object": {
        "en": "circuit {n}: must be an object (got {got})",
        "es": "circuito {n}: debe ser un objeto (recibido {got})",
    },
    "err_circuit_unknown_keys": {
        "en": "circuit {n}: unknown key(s) {keys}",
        "es": "circuito {n}: clave(s) desconocida(s) {keys}",
    },
    "err_circuits_empty": {
        "en": "circuits must be a non-empty list of circuit objects",
        "es": "circuits debe ser una lista no vacía de objetos de circuito",
    },
    "err_duplicate_tags": {
        "en": "duplicate circuit tag(s): {tags}",
        "es": "etiqueta(s) de circuito duplicada(s): {tags}",
    },
    "err_not_positive_number": {
        "en": "{name} must be a positive finite number (got {value!r})",
        "es": "{name} debe ser un número finito positivo (recibido {value!r})",
    },
    "err_not_text": {
        "en": "{name} must be a non-empty string (got {value!r})",
        "es": "{name} debe ser un texto no vacío (recibido {value!r})",
    },
    "err_phases_not_1_or_3": {
        "en": "{where}: phases must be 1 or 3 (got {value!r})",
        "es": "{where}: las fases deben ser 1 o 3 (recibido {value!r})",
    },
    "err_start_strip_name": {
        "en": "start_strip must be a name of letters, digits, - and _ starting with a letter (got {start_strip!r})",
        "es": "start_strip debe ser un nombre de letras, dígitos, - y _ que empiece con una letra (recibido {start_strip!r})",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
