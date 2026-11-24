"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_logo_layer_company": {
        "en": "a logo layer needs the name of a company (letters or digits)",
        "es": "una capa de logo necesita el nombre de una empresa (letras o dígitos)",
    },
    "err_verify_min_length": {
        "en": "min_length must be a finite number > 0 in drawing units (got {value!r})",
        "es": "min_length debe ser un número finito mayor que 0 en unidades de dibujo (recibido {value!r})",
    },
    "err_verify_unknown_rule": {
        "en": "unknown verification rule(s): {rules}",
        "es": "regla(s) de verificación desconocida(s): {rules}",
    },
    "err_stamp_date_type": {
        "en": "stamp date must be an ISO date or datetime, not {type_name}",
        "es": "la fecha del sello debe ser una fecha o fecha y hora ISO, no {type_name}",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
