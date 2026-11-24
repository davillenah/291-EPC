"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_unknown_library": {
        "en": "unknown symbol library {kind!r}; expected one of {kinds}",
        "es": "biblioteca de símbolos desconocida {kind!r}; se esperaba una de {kinds}",
    },
    "err_placeholder_name": {
        "en": "a stand-in box needs the name of the symbol",
        "es": "la caja provisoria necesita el nombre del símbolo",
    },
    "err_placeholder_size": {
        "en": "{field} must be greater than zero, got {value}",
        "es": "{field} debe ser mayor que cero, se recibió {value}",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
