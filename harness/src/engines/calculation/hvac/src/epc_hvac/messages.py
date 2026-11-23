"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_design_missing": {
        "en": "design is missing: {missing}",
        "es": "falta design: {missing}",
    },
    "err_input_not_json": {
        "en": "the input is not valid JSON: {e}",
        "es": "la entrada no es JSON válido: {e}",
    },
    "err_orientation_invalid": {
        "en": "orientation must be one of {allowed} (got {orientation!r})",
        "es": "orientation debe ser una de {allowed} (recibido {orientation!r})",
    },
    "err_out_of_range": {
        "en": "{name} must be {relation} (got {got})",
        "es": "{name} debe ser {relation} (recibido {got})",
    },
    "err_shgc_range": {
        "en": "shgc must be between 0 and 1 (got {shgc})",
        "es": "shgc debe estar entre 0 y 1 (recibido {shgc})",
    },
    "err_space_incomplete": {
        "en": "every space needs `id` and `area_m2`",
        "es": "cada local necesita `id` y `area_m2`",
    },
    "err_spaces_empty": {
        "en": "the input needs a non-empty list `spaces`",
        "es": "la entrada necesita una lista no vacía `spaces`",
    },
    "err_supply_delta_t": {
        "en": "supply_delta_t_k must be > 0",
        "es": "supply_delta_t_k debe ser > 0",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
