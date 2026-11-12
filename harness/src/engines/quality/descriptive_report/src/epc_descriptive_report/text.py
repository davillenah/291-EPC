"""Spanish plain text of the descriptive report: string templates and the document's values only (no number is written in a template).

A sentence whose values are missing is left out; nothing is invented.
"""

HEADER = "MEMORIA DESCRIPTIVA (borrador)"
SECTION_TITLES = {"object_scope": "Objeto y alcance", "supply_earthing": "Alimentacion y puesta a tierra", "board_organisation": "Organizacion del tablero",
                  "cables_installation": "Cables e instalacion", "protection_earthing": "Proteccion y puesta a tierra", "standards": "Normas aplicables",
                  "status_limitations": "Estado y limitaciones de este borrador"}
ISSUES_TITLE = "Observaciones"
NOT_SPECIFIED = "not specified"
NOT_SPECIFIED_TEXT = "sin especificar"
REVIEW_NOTE = "Los valores copiados conservan su fuente y su estado de revision; ninguna persona verifico un valor marcado como pendiente de revision."

OBJECT = "Esta memoria describe la instalacion del proyecto {project_code}"
OBJECT_CLIENT = ", del cliente {client_name}"
OBJECT_SITE = ", ubicada en {site_address}"
OBJECT_COUNTRY = " ({site_country})"
OBJECT_TYPE = " Tipo de instalacion: {site_installation_type}."
SUPPLY_SOURCE = "La instalacion se alimenta desde {supply_source}."
SUPPLY_VOLTAGE = " La tension de alimentacion es {supply_voltage}."
SUPPLY_EARTHING = " El esquema de puesta a tierra es {earthing_system}."
SUPPLY_LEVEL = " El nivel de cortocircuito disponible es {short_circuit_level}"
SUPPLY_ORIGIN = ", segun {short_circuit_origin}"
BOARD_TOTAL = "El tablero esta compuesto por {circuits_total} circuitos."
BOARD_TYPES = " Segun su tipo: {listing}."
BOARD_PHASES = " Segun sus fases: {listing}."
CABLES_COUNT = "Se emplean {cable_specs_distinct} especificaciones de cable distintas: {listing}."
CABLES_TERMINALS = " La lista de bornes contiene {terminals_total} bornes."
CABLES_BOQ = " El computo preliminar tiene {boq_lines} lineas, {boq_devices} dispositivos de proteccion y {boq_cable_m}."
PROTECTION_DEVICES = "Los dispositivos de proteccion presentes son: {listing}."
PROTECTION_EARTHING = " El esquema de puesta a tierra es {earthing_system}."
PROTECTION_TIMES = " Tiempos de desconexion considerados: {listing}."
STANDARDS_JURISDICTION = "La jurisdiccion normativa es {jurisdiction}."
STANDARDS_REVISIONS = " Revisiones aplicables: {listing}."
STANDARDS_CRITERIA = " Conjunto de criterios de diseno: {criteria_set}."
STATUS_NOTICE = "Este documento es un borrador y no puede aprobarse para construccion mientras algun valor de norma este sin revisar ({reference})."
STATUS_PENDING = " Documentos pendientes: {listing}."
STATUS_UNREVIEWED = " Registros de norma sin revisar: {unreviewed_norm_records}."
STATUS_OPEN = " Requisitos abiertos de la base de diseno: {open_requirements}."
LISTING_ITEM = "{name}: {value}"
CABLE_ITEM = "{material}, {insulation}, seccion {section} {unit}: {count} circuitos"
CABLE_ITEM_NO_SECTION = "{material}, {insulation}, seccion {unspecified}: {count} circuitos"
VALUE_UNIT = "{value} {unit}"


def shown(entry, with_unit=True):
    """The value of an item (with its unit unless with_unit is false), or None when the item has no value."""
    value = None if entry is None else entry.get("value")
    if value is None or value == "":
        return None
    return VALUE_UNIT.format(value=value, unit=entry["unit"]) if with_unit and entry.get("unit") else str(value)


def by_key(section):
    return {i["key"]: i for i in section["items"]}


def with_prefix(section, prefix):
    return [i for i in section["items"] if i["key"].startswith(prefix)]


def fill(template, **values):
    """The template filled, or an empty text when any value is missing."""
    if any(v is None for v in values.values()):
        return ""
    return template.format(**values)


def named(entries, label_of, with_unit=True):
    return "; ".join(LISTING_ITEM.format(name=label_of(e), value=shown(e, with_unit)) for e in entries if shown(e) is not None)


def suffix(entry):
    return entry["key"].split(".", 1)[1]


def plain(entry):
    return suffix(entry).replace(NOT_SPECIFIED, NOT_SPECIFIED_TEXT)


def object_text(section):
    k = by_key(section)
    code = shown(k.get("project_code"))
    if code is None:
        return ""
    text = fill(OBJECT, project_code=code)
    site = fill(OBJECT_SITE, site_address=shown(k.get("site_address")))
    text += fill(OBJECT_CLIENT, client_name=shown(k.get("client_name"))) + site
    text += fill(OBJECT_COUNTRY, site_country=shown(k.get("site_country"))) if site else ""
    return text + "." + fill(OBJECT_TYPE, site_installation_type=shown(k.get("site_installation_type")))


def supply_text(section):
    k = by_key(section)
    text = fill(SUPPLY_SOURCE, supply_source=shown(k.get("supply_source")))
    text += fill(SUPPLY_VOLTAGE, supply_voltage=shown(k.get("supply_voltage")))
    text += fill(SUPPLY_EARTHING, earthing_system=shown(k.get("earthing_system")))
    level = fill(SUPPLY_LEVEL, short_circuit_level=shown(k.get("short_circuit_level")))
    return text + (level + fill(SUPPLY_ORIGIN, short_circuit_origin=shown(k.get("short_circuit_origin"))) + "." if level else "")


def board_text(section):
    k = by_key(section)
    total = shown(k.get("circuits_total"), False)
    if total is None:
        return ""
    types = named(with_prefix(section, "circuits_by_type."), plain, False)
    phases = named(with_prefix(section, "circuits_by_phases."), plain, False)
    return fill(BOARD_TOTAL, circuits_total=total) + (fill(BOARD_TYPES, listing=types) if types else "") + (fill(BOARD_PHASES, listing=phases) if phases else "")


def cable_item(entry):
    spec = entry["spec"]
    if spec["section"] is None:
        return CABLE_ITEM_NO_SECTION.format(material=spec["material"], insulation=spec["insulation"], unspecified=NOT_SPECIFIED_TEXT, count=entry["value"])
    return CABLE_ITEM.format(material=spec["material"], insulation=spec["insulation"], section=spec["section"], unit=spec["section_unit"], count=entry["value"])


def cables_text(section):
    k = by_key(section)
    listing = "; ".join(cable_item(i) for i in with_prefix(section, "cable_spec."))
    text = fill(CABLES_COUNT, cable_specs_distinct=shown(k.get("cable_specs_distinct"), False), listing=listing or None)
    text += fill(CABLES_TERMINALS, terminals_total=shown(k.get("terminals_total"), False))
    return text + fill(CABLES_BOQ, boq_lines=shown(k.get("boq_lines"), False), boq_devices=shown(k.get("boq_devices"), False), boq_cable_m=shown(k.get("boq_cable_m")))


def protection_text(section):
    k = by_key(section)
    devices = named(with_prefix(section, "protective_device."), plain, False)
    times = named(with_prefix(section, "disconnection_time."), lambda e: e["label"])
    text = fill(PROTECTION_DEVICES, listing=devices or None)
    text += fill(PROTECTION_EARTHING, earthing_system=shown(k.get("earthing_system")))
    return text + fill(PROTECTION_TIMES, listing=times or None)


def standards_text(section):
    k = by_key(section)
    revisions = named(with_prefix(section, "revision."), lambda e: e["label"])
    text = fill(STANDARDS_JURISDICTION, jurisdiction=shown(k.get("jurisdiction")))
    text += fill(STANDARDS_REVISIONS, listing=revisions or None)
    return text + fill(STANDARDS_CRITERIA, criteria_set=shown(k.get("criteria_set")))


def status_text(section):
    k = by_key(section)
    pending = "; ".join(LISTING_ITEM.format(name=suffix(i), value=i["value"]) for i in with_prefix(section, "pending.") if i["value"] is not None)
    text = fill(STATUS_NOTICE, reference=(k.get("draft_notice") or {}).get("source"))
    text += fill(STATUS_PENDING, listing=pending or None)
    text += fill(STATUS_UNREVIEWED, unreviewed_norm_records=shown(k.get("unreviewed_norm_records"), False))
    return text + fill(STATUS_OPEN, open_requirements=shown(k.get("open_requirements"), False))


WRITERS = {"object_scope": object_text, "supply_earthing": supply_text, "board_organisation": board_text, "cables_installation": cables_text,
           "protection_earthing": protection_text, "standards": standards_text, "status_limitations": status_text}


def descriptive_report_to_text(doc):
    """Spanish plain text of a document built by `build_descriptive_report`."""
    if not isinstance(doc, dict) or not isinstance(doc.get("sections"), list):
        raise ValueError("a descriptive-report document with sections is required")
    lines = [HEADER, ""]
    for n, section in enumerate(doc["sections"], start=1):
        body = WRITERS.get(section["id"], lambda _s: "")(section).strip()
        lines += [f"{n}. {SECTION_TITLES.get(section['id'], section['title'])}"] + ([body] if body else []) + [""]
    lines += [REVIEW_NOTE, ""]
    if doc.get("issues"):
        lines += [ISSUES_TITLE] + [f"- {row}" for row in doc["issues"]] + [""]
    return "\n".join(lines)
