"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_sld_file_missing": {
        "en": "{field}: the file {path} does not exist",
        "es": "{field}: el archivo {path} no existe",
    },
    "err_sld_field_missing": {
        "en": "{field} is required: the single-line diagram only draws, the calculation comes from the caller",
        "es": "falta {field}: el unifilar solo dibuja, el cálculo lo entrega quien llama",
    },
    "err_sld_format_invalid": {
        "en": "formato must be 'A1' or 'A3' (got {value!r})",
        "es": "formato debe ser 'A1' o 'A3' (recibido {value!r})",
    },
    "err_sld_maxl_invalid": {
        "en": "maxl must be an integer of 1 or more (got {value!r})",
        "es": "maxl debe ser un entero mayor o igual que 1 (recibido {value!r})",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The English and Spanish text of `code` with its parameters filled in."""
    m = MESSAGES[code]
    return {"en": m["en"].format(**params), "es": m["es"].format(**params)}
