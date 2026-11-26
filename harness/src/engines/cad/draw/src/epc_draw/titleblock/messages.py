"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_png_invalid": {
        "en": "{basename} is not a valid PNG",
        "es": "{basename} no es un PNG válido",
    },
    "err_svg_no_size": {
        "en": "{basename} has no viewBox and no width/height",
        "es": "{basename} no tiene viewBox ni width/height",
    },
    "err_config_invalid": {
        "en": "the sheet configuration is not valid: {details}",
        "es": "la configuración de la lámina no es válida: {details}",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
