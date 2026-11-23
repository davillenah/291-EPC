"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_circuit_section_invalid": {
        "en": "circuit {tag}: s_mm2 must be a number greater than zero",
        "es": "circuito {tag}: s_mm2 debe ser un número mayor que cero",
    },
    "err_circuit_tag_duplicate": {
        "en": "circuit {n}: duplicate tag {tag}",
        "es": "circuito {n}: etiqueta duplicada {tag}",
    },
    "err_circuit_tag_missing": {
        "en": "circuit {n}: a tag (non-empty text) is required",
        "es": "circuito {n}: falta la etiqueta (texto no vacío)",
    },
    "err_circuits_empty": {
        "en": "circuits must be a non-empty list",
        "es": "circuits debe ser una lista no vacía",
    },
    "err_design_basis_invalid": {
        "en": "design_basis must be a design-basis document (a dict with a list of sections)",
        "es": "design_basis debe ser un documento de bases de diseño (un dict con una lista de secciones)",
    },
    "err_not_dict": {
        "en": "{name} must be a dict when given",
        "es": "{name} debe ser un dict cuando se indica",
    },
    "err_pending_documents_invalid": {
        "en": "pending_documents must be a list of dicts with a name",
        "es": "pending_documents debe ser una lista de dicts con un nombre",
    },
    "err_report_document_required": {
        "en": "a descriptive-report document with sections is required",
        "es": "se requiere un documento de memoria descriptiva con secciones",
    },
    "err_unreviewed_records_invalid": {
        "en": "unreviewed_norm_records must be a whole number, zero or more",
        "es": "unreviewed_norm_records debe ser un entero de cero o más",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
