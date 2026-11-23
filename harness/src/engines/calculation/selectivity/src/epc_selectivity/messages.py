"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_rated_current": {
        "en": "In must be positive",
        "es": "In debe ser positiva",
    },
    "err_type_unknown": {
        "en": "unknown type {tipo}: {tipos}",
        "es": "tipo {tipo} desconocido: {tipos}",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
