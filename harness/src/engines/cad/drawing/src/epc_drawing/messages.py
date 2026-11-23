"""Every error the engine can raise, in English (source) and Spanish. A message is a code with two templates; `{name}` is filled in from the call (ADR-0039)."""
from typing import Dict

MESSAGES: Dict[str, Dict[str, str]] = {
    "err_assembly_needs_audit": {
        "en": "the assembly needs the audit verdict of the board (diagram_knowledge.audit)",
        "es": "el ensamblado necesita el veredicto de auditoría del tablero (diagram_knowledge.audit)",
    },
    "err_drawing_date_type": {
        "en": "drawing date must be an ISO date, not {type_name}",
        "es": "la fecha del dibujo debe ser una fecha ISO, no {type_name}",
    },
    "err_format_invalid": {
        "en": "the format must be one of {formats}",
        "es": "el formato debe ser uno de {formats}",
    },
    "err_layout_no_tables": {
        "en": "the layout has no tables to raise in 3D",
        "es": "la disposición no tiene mesas para elevar en 3D",
    },
    "err_plan_empty": {
        "en": "the plan has nothing drawn",
        "es": "el plano no tiene nada dibujado",
    },
    "err_roof_no_planes": {
        "en": "the roof has no planes to raise in 3D",
        "es": "el techo no tiene faldones para elevar en 3D",
    },
    "err_sheet_no_zone": {
        "en": "the sheet does not say its usable zone: it is not an IRAM sheet of epc_titleblock",
        "es": "la lámina no indica su zona útil: no es una lámina IRAM de epc_titleblock",
    },
    "err_sheet_not_dxf": {
        "en": "the sheet could not be made as a DXF: {reason}",
        "es": "no se pudo hacer la lámina como DXF: {reason}",
    },
}


def text(code: str, **params) -> Dict[str, str]:
    """The message `code` in both languages with its parameters filled in."""
    entry = MESSAGES[code]
    return {lang: entry[lang].format(**params) for lang in ("en", "es")}
