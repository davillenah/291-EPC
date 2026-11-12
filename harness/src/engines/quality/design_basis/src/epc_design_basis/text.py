"""Spanish plain text of the design-basis document: string templates and the document's values only (no number is written in a template)."""

HEADER = "BASE DE DISENO (borrador)"
SECTION_TITLES = {"identification": "Identificacion del proyecto", "supply": "Datos de alimentacion", "normative_profile": "Perfil normativo",
                  "design_criteria": "Criterios de diseno y limites", "assumptions": "Supuestos", "requirements": "Requisitos y puntos abiertos",
                  "values_note": "Que significan los valores"}
LABELS = {"project_code": "Codigo de proyecto", "client_name": "Cliente", "site_address": "Sitio", "site_country": "Pais", "site_installation_type": "Tipo de instalacion",
          "language": "Idioma", "supply_source": "Fuente de alimentacion", "supply_voltage": "Tension de alimentacion", "earthing_system": "Esquema de puesta a tierra",
          "short_circuit_level": "Nivel de cortocircuito", "short_circuit_origin": "Origen del nivel de cortocircuito", "jurisdiction": "Jurisdiccion",
          "criteria_set": "Conjunto de criterios de diseno", "criteria_exceptions": "Excepciones a los criterios", "c_min": "Factor de tension c minimo",
          "system_voltage_to_earth": "Tension fase-tierra del sistema", "what_the_values_mean": "Nota"}
PREFIXES = (("voltage_drop_limit.", "Limite de caida de tension: "), ("disconnection_time.sectional.", "Tiempo maximo de desconexion de seccionales: "),
            ("disconnection_time.table.", "Tiempo maximo de desconexion segun tension: "), ("insulation_by_role.", "Aislacion segun el rol: "),
            ("revision.", "Revision de "), ("A-", "Supuesto "), ("R-", "Requisito "))
NOTE_TEXT = "Los limites listados son los que aplicaran los motores de calculo, leidos de sus propios datos. Un estado pendiente de revision indica que ninguna persona verifico el valor. Este documento es un borrador."
STATUS_WORDS = {"verified": "verificado", "pending review": "pendiente de revision", "rejected": "rechazado"}
EMPTY = "sin dato"
ISSUES_TITLE = "Observaciones"
OPEN_TITLE = "Puntos abiertos"
SOURCE_WORD, STATUS_WORD, REASON_WORD, SITUATION_WORD = "fuente", "estado", "motivo", "situacion"


def label_of(entry):
    key = str(entry["key"])
    if key in LABELS:
        return LABELS[key]
    for prefix, template in PREFIXES:
        if key.startswith(prefix):
            return template + (key[len(prefix):] if prefix not in ("A-", "R-") else key)
    return str(entry.get("label"))


def value_text(entry):
    value = entry.get("value")
    if value is None or value == [] or value == "":
        return EMPTY
    shown = ", ".join(str(v) for v in value) if isinstance(value, list) else str(value)
    return f"{shown} {entry['unit']}" if entry.get("unit") else shown


def tail(entry):
    parts = []
    if entry.get("source"):
        parts.append(f"{REASON_WORD if str(entry['key']).startswith('A-') else SOURCE_WORD}: {entry['source']}")
    if entry.get("status"):
        parts.append(f"{SITUATION_WORD}: {entry['status']}")
    if entry.get("review_status"):
        parts.append(f"{STATUS_WORD}: {STATUS_WORDS.get(entry['review_status'], entry['review_status'])}")
    return f" ({'; '.join(parts)})" if parts else ""


def item_line(entry):
    if entry["key"] == "what_the_values_mean":
        return f"- {label_of(entry)}: {NOTE_TEXT}"
    return f"- {label_of(entry)}: {value_text(entry)}{tail(entry)}"


def design_basis_to_text(doc):
    """Spanish plain text of a document built by `build_design_basis_document`."""
    if not isinstance(doc, dict) or "sections" not in doc:
        raise ValueError("a design-basis document with sections is required")
    lines = [HEADER, ""]
    for n, section in enumerate(doc["sections"], start=1):
        lines += [f"{n}. {SECTION_TITLES.get(section['id'], section['title'])}"] + [item_line(i) for i in section["items"]] + [""]
    for title, rows in ((OPEN_TITLE, doc.get("open_items") or []), (ISSUES_TITLE, doc.get("issues") or [])):
        if rows:
            lines += [title] + [f"- {row}" for row in rows] + [""]
    return "\n".join(lines)
