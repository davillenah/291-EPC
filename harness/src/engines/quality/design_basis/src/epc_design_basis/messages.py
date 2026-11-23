"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_assumption_incomplete": {
        "en": "assumption {n}: text and reason are both required",
        "es": "supuesto {n}: se requieren el texto y el motivo",
    },
    "err_d24_missing": {
        "en": "D24 data missing in the profile: {missing}",
        "es": "faltan datos D24 en el perfil: {missing}",
    },
    "err_document_required": {
        "en": "a design-basis document with sections is required",
        "es": "se requiere un documento de bases de diseño con secciones",
    },
    "err_insulation_rules_invalid": {
        "en": "insulation_rules must map a role to an insulation name",
        "es": "insulation_rules debe asociar un rol con el nombre de una aislación",
    },
    "err_norm_status_invalid": {
        "en": "norm_status must map register ids to one of {allowed}",
        "es": "norm_status debe asociar ids del registro con uno de {allowed}",
    },
    "err_profile_not_object": {
        "en": "the profile must be an object",
        "es": "el perfil debe ser un objeto",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
