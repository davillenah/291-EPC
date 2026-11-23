"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_drop_not_positive": {
        "en": "R*cos(phi) + X*sin(phi) <= 0: the drop is not positive, the maximum length is undefined",
        "es": "R·cosφ + X·senφ ≤ 0: la caída no es positiva, longitud máxima indefinida",
    },
    "err_material_phases": {
        "en": "material 'cu'|'al' and fases 1|3",
        "es": "material 'cu'|'al' y fases 1|3",
    },
    "err_not_finite_number": {
        "en": "{nombre} must be a finite number (got: {valor!r})",
        "es": "{nombre} debe ser un número finito (recibido: {valor!r})",
    },
    "err_out_of_range": {
        "en": "{nombre} must be {op} {minimo} (got: {valor})",
        "es": "{nombre} debe ser {op} {minimo} (recibido: {valor})",
    },
    "err_phases_invalid": {
        "en": "fases must be 1 or 3 (got: {fases!r})",
        "es": "fases debe ser 1 o 3 (recibido: {fases!r})",
    },
    "err_power_factor": {
        "en": "fp must be in [0, 1] (got: {fp})",
        "es": "fp debe estar en [0, 1] (recibido: {fp})",
    },
    "err_section_not_in_table": {
        "en": "section {seccion_mm2} is not in Table 771.19.IV: {tabla}",
        "es": "sección {seccion_mm2} no está en la Tabla 771.19.IV: {tabla}",
    },
    "err_starting_gdc": {
        "en": "starting GDC is defined up to {maximo} mm²",
        "es": "GDC de arranque definido hasta {maximo} mm²",
    },
    "err_type_invalid": {
        "en": "tipo must be one of {opciones}",
        "es": "tipo debe ser uno de {opciones}",
    },
    "err_type_lighting_or_receptacles": {
        "en": "tipo must be 'iluminacion' or 'tomacorrientes'",
        "es": "tipo debe ser 'iluminacion' o 'tomacorrientes'",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
