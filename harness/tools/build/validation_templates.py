#!/usr/bin/env python3
"""Validation templates for the owner's tasks MIG-40 and MIG-42 (generated, never filled in).

  python harness/tools/build/validation_templates.py           write both workbooks into harness/docs/validation/
  python harness/tools/build/validation_templates.py --check   exit 1 when the files on disk differ from what this script generates

Workbooks (the owner reads them, so headers and instructions are in Spanish; the code is English):

* `norm_verification_worksheet.xlsx` - one row per item of the norm register (hand records and auto-indexed rules), in the order of plan MIG-40:
  1 conflicts or duplicates, 2 no clause, 3 Part 771, 4 Parts 770/701/722, 5 scanned Parts 4 and 5, then `Sin clasificar`. The register columns are copied
  and never edited; the owner columns (official value, clause, page, verdict, corrected value, notes, date, signature) are EMPTY.
* `spike_309kva_input_template.xlsx` - the input template of the 309 kVA golden project (PRD section 21): profile, loads, requirements, and the reference
  values and tolerances the owner calculates independently. Every value column is EMPTY.

This tool only READS the norm register (`norm_register.py`); it never changes a norm value or a review state. `--check` compares the CELL CONTENT of the files
(an .xlsx zip is not byte-deterministic). Frozen decisions D15 (raceway fill) and D26 (simplified rod formula) are only flagged in the worksheet.
"""
import argparse
import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import epc_paths as P  # noqa: E402
import norm_register as N  # noqa: E402
from openpyxl import Workbook, load_workbook  # noqa: E402
from openpyxl.styles import Alignment, Font, PatternFill  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402
from openpyxl.worksheet.datavalidation import DataValidation  # noqa: E402

REPO = P.REPO
OUT_DIR = P.DOCS / "validation"
WORKSHEET = "norm_verification_worksheet.xlsx"
SPIKE = "spike_309kva_input_template.xlsx"
FIXED_TIME = datetime(2026, 11, 12, 0, 0, 0)
CREATOR = "EPC-291 validation_templates.py"
MAX_VALUE_CHARS = 1500
NO_CLAUSE = "sin cláusula"
VERDICTS = ("Verificado", "Corregir", "Rechazar", "Pendiente")
SHEET_VERIF = "Verificación"
BLANK_ROWS = {"Cargas": 40, "Áreas": 20, "Requisitos": 40}

# ------------------------------------------------------------------ groups of the worksheet (order of plan MIG-40)
GROUPS = ("1 - Conflictos o duplicados", "2 - Sin cláusula", "3 - Parte 771 (AEA 90364-7-771)", "4 - Partes 770, 701 y 722",
          "5 - Partes 4 y 5 (escaneadas)", "Sin clasificar")
P771 = re.compile(r"90364-7-771")
P_OTHER = {"770": 0, "701": 1, "722": 2}                 # order inside group 4
P_OTHER_RX = re.compile(r"90364-7-(770|701|722)")
SCANNED = re.compile(r"90364-[45]-")
# Frozen decisions: detection is by record id (documented in the Instrucciones sheet).
D15_RX = re.compile(r"raceway-fill|occupancy\.(tray|conduit)_pct|canalizaciones-llenado")
D26_RX = re.compile(r"resistance_rod\.simplificada")
D15_TEXT = "Sí (D15)"
D26_TEXT = "Sí (D26)"

# Columns of the worksheet: (header, width, filled by the owner)
PREFILLED = [("Orden", 7), ("Grupo", 26), ("Id del registro", 42), ("Motor/paquete", 16), ("Norma y edición", 24), ("Tema", 44),
             ("Valor actual en el código o datos", 48), ("Unidad", 9), ("Cláusula", 20), ("Página/fuente", 38), ("Procedencia", 20),
             ("Estado actual", 16), ("Observaciones del registro", 48), ("Congelado", 11)]
OWNER = [("Valor oficial", 20), ("Cláusula oficial", 18), ("Página oficial", 12), ("Veredicto", 13), ("Valor corregido", 20), ("Notas", 36),
         ("Fecha", 12), ("Firma", 16)]
HEADERS = [h for h, _ in PREFILLED + OWNER]
COL = {h: get_column_letter(i + 1) for i, h in enumerate(HEADERS)}

HEAD_FILL = PatternFill("solid", fgColor="1F3864")
OWNER_HEAD_FILL = PatternFill("solid", fgColor="BF8F00")
LOCKED_FILL = PatternFill("solid", fgColor="EDEDED")
OWNER_FILL = PatternFill("solid", fgColor="FFF2CC")
HEAD_FONT = Font(bold=True, color="FFFFFF")
WRAP = Alignment(wrap_text=True, vertical="top")
HEAD_ALIGN = Alignment(wrap_text=True, vertical="center", horizontal="center")


# ------------------------------------------------------------------ text helpers
_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def clean(text) -> str:
    return _ILLEGAL.sub("", str(text))


def put(ws, row, col, value, style=None):
    """Set a cell. A string is always stored as text (a leading `=` never becomes a formula) unless `style='formula'`."""
    cell = ws.cell(row=row, column=col)
    if isinstance(value, str) and style != "formula":
        cell.value = clean(value)
        cell.data_type = "s"
    else:
        cell.value = value
    return cell


def json_text(value) -> str:
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= MAX_VALUE_CHARS else text[:MAX_VALUE_CHARS] + " ... (cortado; ver el archivo)"


def page_text(page) -> str:
    if not isinstance(page, dict):
        return ""
    parts = []
    if page.get("printed") not in (None, ""):
        parts.append(f"p. {page['printed']}")
    if page.get("pdf") is not None:
        parts.append(f"PDF {page['pdf']}")
    return " / ".join(parts)


def norm_text(norm, edition) -> str:
    return " ".join(x for x in (norm, f"({edition})" if edition else "") if x)


# ------------------------------------------------------------------ the register items
def review_state(reg, point):
    rec = reg.review.get(point) if point else None
    return rec.get("status") if isinstance(rec, dict) else "pending"


def hand_value(reg, r):
    """(value text, location text) of a hand record: JSON records are resolved through their pointer, code records carry the literal."""
    loc = r.get("location", {})
    name = str(loc.get("file", "")).rsplit("/", 1)[-1]
    if loc.get("type") == "code":
        return json_text(r.get("value")), f"{name}:{loc.get('line')} {loc.get('symbol') or ''}".strip()
    ok, got = N.resolve_pointer(reg.doc(loc["file"]), loc["pointer"])
    return (json_text(got) if ok else "(no se pudo leer)"), f"{name}#{loc.get('pointer', '')}"


def hand_item(reg, engines, rel, r):
    value, where = hand_value(reg, r)
    state = r.get("status", "")
    rev = review_state(reg, r.get("review_point"))
    issues = list(r.get("issues") or [])
    obs = "; ".join(issues + ([f"Nota: {r['note']}"] if r.get("note") else []))
    page = page_text(r.get("page"))
    return {"id": r["id"], "engine": engines.get(rel, ""), "norm": r.get("norm"), "norm_text": norm_text(r.get("norm"), r.get("edition")),
            "topic": (r.get("title") or {}).get("es", ""), "value": value, "unit": r.get("unit") or "", "clause": r.get("clause"),
            "source": " | ".join(x for x in (page, where) if x), "prov": f"{r.get('provenance')} / {r.get('verification')}",
            "state": state + (f" (revisión: {rev})" if rev not in (None, "pending") else ""), "obs": obs,
            "conflict": any(N.CONFLICT.match(i) for i in issues)}


def auto_rule(reg, a):
    """The rule dict an auto-indexed record points to (rule id = second half of its review point)."""
    key = "reglas" if a["engine"] == "aea90364" else "rules"
    rule_id = a["review_point"].split("|", 1)[1]
    return next((r for r in reg.doc(a["file"]).get(key, []) if r.get("id") == rule_id), {})


def auto_value(rule):
    """(value text, unit) of an auto-indexed rule: AEA rules carry text and parameters, lighting rules a value with its unit."""
    if "parametros" in rule or "regla" in rule:
        text = " ".join(x for x in (rule.get("regla"), json_text(rule["parametros"]) if rule.get("parametros") else "") if x)
        return text, ""
    return json_text(rule.get("value")), rule.get("unit") or ""


def auto_item(reg, a):
    value, unit = auto_value(auto_rule(reg, a))
    return {"id": a["id"], "engine": a["engine"], "norm": a["norm"], "norm_text": norm_text(a["norm"], a["edition"]), "topic": a["title"], "value": value,
            "unit": unit, "clause": a["clause"], "source": " | ".join(x for x in (page_text(a["page"]), a["file"].rsplit("/", 1)[-1]) if x),
            "prov": f"norm / {a['verification']}", "state": a["review"] or "pending", "obs": "", "conflict": False}


def collect_items(reg) -> list:
    engines = {rel: data.get("engine", "") for rel, data in reg.files}
    items = [hand_item(reg, engines, rel, r) for rel, r in reg.records]
    return items + [auto_item(reg, a) for a in reg.auto]


def group_of(item) -> int:
    """1-based group of an item; the FIRST group that applies wins."""
    norm = item["norm"] or ""
    if item["conflict"]:
        return 1
    if not item["clause"]:
        return 2
    for number, rx in ((3, P771), (4, P_OTHER_RX), (5, SCANNED)):
        if rx.search(norm):
            return number
    return 6


def frozen_text(item_id) -> str:
    if D15_RX.search(item_id):
        return D15_TEXT
    return D26_TEXT if D26_RX.search(item_id) else ""


def sort_key(item, index):
    """Group, then the part order inside group 4, then the norm, then the register order."""
    group = group_of(item)
    m = P_OTHER_RX.search(item["norm"] or "")
    sub = P_OTHER[m.group(1)] if group == 4 and m else 0
    return (group, sub, item["norm"] or "" if group >= 5 else "", index)


def ordered_rows(reg) -> list:
    """The worksheet rows: [(group number, item)] ordered as plan MIG-40, ids unique."""
    items = collect_items(reg)
    ranked = sorted(enumerate(items), key=lambda t: sort_key(t[1], t[0]))
    seen, rows = set(), []
    for _, item in ranked:
        if item["id"] not in seen:
            seen.add(item["id"])
            rows.append((group_of(item), item))
    return rows


# ------------------------------------------------------------------ sheet helpers
def style_header(ws, row, headers, owner_from=None):
    for i, h in enumerate(headers, start=1):
        c = put(ws, row, i, h)
        c.font = HEAD_FONT
        c.alignment = HEAD_ALIGN
        c.fill = OWNER_HEAD_FILL if owner_from is not None and i >= owner_from else HEAD_FILL
    ws.row_dimensions[row].height = 32


def set_widths(ws, widths):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def add_list(ws, options, sqref, formula=None):
    dv = DataValidation(type="list", formula1=formula or '"' + ",".join(options) + '"', allow_blank=True)
    dv.add(sqref)
    ws.add_data_validation(dv)


def text_sheet(ws, lines, width=110):
    """A sheet of wrapped lines: a line starting with `# ` is a heading."""
    ws.column_dimensions["A"].width = width
    for r, line in enumerate(lines, start=1):
        head = line.startswith("# ")
        c = put(ws, r, 1, line[2:] if head else line)
        c.alignment = WRAP
        c.font = Font(bold=head, size=14 if r == 1 else 11)


def finish(wb):
    wb.properties.creator = CREATOR
    wb.properties.lastModifiedBy = CREATOR
    wb.properties.created = FIXED_TIME
    wb.properties.modified = FIXED_TIME
    return wb


# ------------------------------------------------------------------ worksheet: Instrucciones, Verificación, Resumen
INSTRUCTIONS_WS = [
    "# Planilla de verificación de valores de norma (tarea MIG-40)",
    "Para qué sirve: cada fila es un valor del registro de normas del proyecto (docs/NORM_REGISTER.md). Usted lo compara con la norma oficial y deja su veredicto. "
    "La planilla la genera una herramienta; no trae ningún valor aprobado y no cambia el registro por sí sola.",
    "",
    "# Cómo se completa",
    "1. Trabaje en el orden de la hoja Verificación (columna Orden): conflictos o duplicados, luego sin cláusula, luego Parte 771, luego Partes 770, 701 y 722, "
    "y por último las Partes 4 y 5 (escaneadas). Las filas 'Sin clasificar' son valores que no caen en ningún grupo anterior.",
    "2. Las columnas grises (Orden a Congelado) vienen del registro y no se editan. Las columnas amarillas son suyas.",
    "3. Para cada fila: busque el valor en la norma oficial y anote Valor oficial, Cláusula oficial y Página oficial; después elija el Veredicto.",
    "4. Si el veredicto es Corregir, escriba el Valor corregido y explique en Notas. Anote Fecha y Firma de cada verificación.",
    "5. La hoja Resumen cuenta sola cuántas filas hay en cada veredicto (las fórmulas se actualizan al completar).",
    "",
    "# Significado del veredicto",
    "Verificado: el valor, la cláusula y la página del registro coinciden con la norma oficial.",
    "Corregir: la norma dice otra cosa (valor, cláusula o página); el valor corregido va en la columna Valor corregido.",
    "Rechazar: el valor no corresponde a la norma o no debe usarse (por ejemplo un valor típico sin respaldo).",
    "Pendiente: todavía no se pudo verificar (falta la norma, página ilegible, duda por consultar). Una fila vacía equivale a no revisada.",
    "",
    "# Importante",
    "Nada de lo que figura aquí está aprobado hasta que usted completa el veredicto. La planilla no modifica el registro de normas ni su estado de revisión: "
    "sus veredictos se incorporan en una sesión posterior, junto con usted.",
    "Congelados: D15 (llenado máximo de canalizaciones, 35 % o 40 %) y D26 (fórmula simplificada de jabalina) están CONGELADOS por decisión del dueño. "
    "Esas filas llevan 'Sí (D15)' o 'Sí (D26)' en la columna Congelado: déjelas en blanco (se resuelven en la tarea MIG-41).",
    "Cómo se detectan las filas congeladas (por el id del registro): D15 = ids que contienen 'raceway-fill', 'occupancy.tray_pct', 'occupancy.conduit_pct' "
    "o 'canalizaciones-llenado'; D26 = id que contiene 'resistance_rod.simplificada'. Si encuentra otra fila ligada a esos temas, déjela en blanco y avise.",
    "Las filas con cláusula en una norma que no es AEA 90364 (IEC, IRAM, NFPA, Decreto 351/79 y otras) o sin parte reconocible quedan en el grupo 'Sin clasificar'.",
]


def verification_sheet(ws, rows):
    n = len(rows)
    style_header(ws, 1, HEADERS, owner_from=len(PREFILLED) + 1)
    set_widths(ws, [w for _, w in PREFILLED + OWNER])
    for r, (group, item) in enumerate(rows, start=2):
        values = [r - 1, GROUPS[group - 1], item["id"], item["engine"], item["norm_text"], item["topic"], item["value"], item["unit"],
                  item["clause"] or NO_CLAUSE, item["source"], item["prov"], item["state"], item["obs"], frozen_text(item["id"])]
        for c, v in enumerate(values, start=1):
            cell = put(ws, r, c, v)
            cell.alignment = WRAP
            cell.fill = LOCKED_FILL
        for c in range(len(PREFILLED) + 1, len(HEADERS) + 1):
            cell = ws.cell(row=r, column=c)
            cell.fill = OWNER_FILL
            cell.alignment = WRAP
        ws.cell(row=r, column=len(HEADERS) - 1).number_format = "yyyy-mm-dd"
    ws.freeze_panes = "D2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(HEADERS))}{n + 1}"
    verdict = COL["Veredicto"]
    add_list(ws, VERDICTS, f"{verdict}2:{verdict}{n + 1}")


def rng(header, n):
    col = COL[header]
    return f"'{SHEET_VERIF}'!${col}$2:${col}${n + 1}"


def summary_sheet(ws, n):
    """Counts as formulas over the Verificación sheet, so they follow the owner's verdicts."""
    ws.column_dimensions["A"].width = 38
    for c in "BCDEFGH":
        ws.column_dimensions[c].width = 15
    put(ws, 1, 1, "Resumen de la verificación (se calcula solo)").font = Font(bold=True, size=14)
    put(ws, 2, 1, "Filas en la hoja Verificación")
    put(ws, 2, 2, f"=COUNTA({rng('Id del registro', n)})", "formula")
    heads = ["Grupo", "Total", *VERDICTS, "En blanco", "Congeladas (D15/D26)"]
    style_header(ws, 4, heads)
    for i, g in enumerate(GROUPS, start=5):
        put(ws, i, 1, g)
        put(ws, i, 2, f"=COUNTIF({rng('Grupo', n)},$A{i})", "formula")
        for c, v in enumerate(VERDICTS, start=3):
            put(ws, i, c, f"=COUNTIFS({rng('Grupo', n)},$A{i},{rng('Veredicto', n)},{get_column_letter(c)}$4)", "formula")
        put(ws, i, 7, f"=B{i}-SUM(C{i}:F{i})", "formula")
        put(ws, i, 8, f'=COUNTIFS({rng("Grupo", n)},$A{i},{rng("Congelado", n)},"Sí*")', "formula")
    total = 5 + len(GROUPS)
    put(ws, total, 1, "Total").font = Font(bold=True)
    put(ws, total, 2, f"=COUNTA({rng('Id del registro', n)})", "formula")
    for c, v in enumerate(VERDICTS, start=3):
        put(ws, total, c, f"=COUNTIF({rng('Veredicto', n)},{get_column_letter(c)}$4)", "formula")
    put(ws, total, 7, f"=B{total}-SUM(C{total}:F{total})", "formula")
    put(ws, total, 8, f'=COUNTIF({rng("Congelado", n)},"Sí*")', "formula")


def build_worksheet(reg) -> Workbook:
    rows = ordered_rows(reg)
    wb = Workbook()
    text_sheet(wb.active, INSTRUCTIONS_WS)
    wb.active.title = "Instrucciones"
    verification_sheet(wb.create_sheet(SHEET_VERIF), rows)
    summary_sheet(wb.create_sheet("Resumen"), len(rows))
    return finish(wb)


# ------------------------------------------------------------------ spike template
STAGES_SRC = P.REPO / "harness" / "src" / "disciplines" / "electrical_lv" / "stages" / "calc_stages.py"
TRANSFORMER = "<transformador>"
# (stage label, output key of calc_stages.py, quantity in Spanish, unit, concept placeholder)
CIRCUIT = "<circuito>"
STAGE8 = "8 - Dimensionamiento de alimentadores y circuitos"
STAGE9 = "9 - Caída de tensión acumulada"
STAGE10 = "10 - Corrientes de cortocircuito"
REFERENCE_QUANTITIES = [
    (STAGE8, "s_mm2", "Sección de fase", "mm²", CIRCUIT), (STAGE8, "pe_mm2", "Sección PE", "mm²", CIRCUIT),
    (STAGE8, "neutral_mm2", "Sección de neutro", "mm²", CIRCUIT), (STAGE8, "ib_a", "Corriente de diseño Ib", "A", CIRCUIT),
    (STAGE8, "in_a", "Corriente nominal In", "A", CIRCUIT), (STAGE8, "iz_a", "Corriente admisible Iz", "A", CIRCUIT),
    (STAGE8, "i2_a", "Corriente de funcionamiento I2", "A", CIRCUIT),
    (STAGE9, "own_pct", "Caída de tensión propia", "%", CIRCUIT), (STAGE9, "accumulated_pct", "Caída de tensión acumulada", "%", CIRCUIT),
    (STAGE10, "icc_a", "Corriente de cortocircuito máxima Icc", "A", CIRCUIT), (STAGE10, "icc_min_a", "Corriente de cortocircuito mínima Icc mín", "A", CIRCUIT),
    (STAGE10, "busbar_icc_ka", "Icc en barras del tablero", "kA", "<tablero>"),
]
BOQ_QUANTITIES = [
    ("15 - Listas y cómputo (BOQ)", "Metros de cable por especificación", "m", "<especificación de cable>"),
    ("15 - Listas y cómputo (BOQ)", "Cantidad de aparatos de protección", "u", "<tipo de aparato>"),
    ("15 - Listas y cómputo (BOQ)", "Cantidad de bornes", "u", "<tamaño de borne>"),
    ("15 - Listas y cómputo (BOQ)", "Cantidad de envolventes", "u", "<tablero>"),
]
REF_HEADERS = ["Etapa", "Concepto (circuito/cálculo)", "Magnitud", "Unidad", "Valor de referencia (calculado de forma independiente)", "Tolerancia (%)",
               "Tolerancia absoluta", "Fuente / método"]
REF_WIDTHS = [44, 28, 40, 9, 26, 14, 16, 40]
TOLERANCES = [
    ("Criterio 2 del spike: resultados de cálculo frente a los valores de referencia", [
        ("Tolerancia relativa aceptada (%)", ""), ("Tolerancia absoluta aceptada (con su unidad)", ""),
        ("Magnitudes a las que aplica (si no son todas)", "")]),
    ("Criterio 4 del spike: cantidades de listas y cómputo (BOQ)", [
        ("Tolerancia relativa aceptada (%)", ""), ("Tolerancia absoluta aceptada (cantidad)", ""),
        ("Listas a las que aplica (cables, aparatos, bornes, ...)", "")]),
    ("Constancia", [("Fecha de la decisión", ""), ("Firma", "")]),
]
INSTRUCTIONS_SPIKE = [
    "# Plantilla de datos del proyecto 309kva_logistics_center (tarea MIG-42)",
    "Para qué sirve: reúne lo que solo usted puede aportar para el spike del PRD §21 sobre el proyecto de referencia de 309 kVA: los datos de entrada del proyecto, "
    "los valores de referencia calculados de forma independiente y las tolerancias. La plantilla se genera con una herramienta y viene vacía: no contiene datos del cliente ni valores inventados.",
    "",
    "# Qué debe completar",
    "Perfil: datos del proyecto (cliente, sitio, alimentación, esquema de puesta a tierra, nivel de cortocircuito disponible, idioma). Complete la columna Valor.",
    "Áreas y Cargas: la lista de cargas por área (iluminación, tomas, motores, especiales), con su potencia, unidad, fases y longitud si la conoce.",
    "Requisitos: requisitos del cliente y del diseño, con su origen y estado.",
    "Valores de referencia: para cada magnitud que el sistema informa por circuito (etapas 8 a 12) y para los cómputos (cables, aparatos, bornes), copie la fila para cada circuito, "
    "reemplace el texto <circuito> por el circuito o ítem real y anote el valor calculado por usted de forma independiente, sin usar el sistema. Anote también la fuente o el método.",
    "Tolerancias: las dos decisiones que usted debe tomar (criterios 2 y 4 del spike).",
    "",
    "# Qué criterios del spike usan estos datos",
    "Criterio 2: «resultados dentro de las tolerancias del dueño frente a valores de referencia calculados de forma independiente» (hoja Valores de referencia y tolerancia del criterio 2).",
    "Criterio 4: «cantidades de listas y cómputo dentro de las tolerancias del dueño» (filas de cómputo y tolerancia del criterio 4).",
    "Los objetivos de costo y tiempo del criterio 9 son aparte (lista de decisiones abiertas del PRD §24, punto 4); no van en este libro.",
    "",
    "# Importante",
    "Las columnas de valor y de tolerancia están vacías a propósito. Ningún número de esta plantilla proviene del sistema ni del código. Los nombres de las magnitudes salen de las "
    "salidas documentadas de las etapas 8 a 12 del sistema, para que la comparación posterior sea directa.",
    "Los textos de descripción de la hoja Perfil, Cargas y Requisitos vienen del esquema de datos y están en inglés.",
]
LABELS = {"project_code": "Código de proyecto", "client.name": "Cliente: nombre", "client.contact": "Cliente: contacto", "site.address": "Sitio: dirección",
          "site.country": "Sitio: país", "site.installation_type": "Sitio: tipo de instalación", "supply.source": "Alimentación: origen",
          "supply.voltage.value": "Tensión: valor", "supply.voltage.unit": "Tensión: unidad", "supply.earthing_system": "Esquema de puesta a tierra",
          "supply.short_circuit_level.value": "Nivel de cortocircuito: valor", "supply.short_circuit_level.unit": "Nivel de cortocircuito: unidad",
          "supply.short_circuit_level.origin": "Nivel de cortocircuito: origen del dato", "criteria.set": "Criterios: conjunto",
          "criteria.exceptions": "Criterios: excepciones", "engineer_of_record.name": "Ingeniero responsable: nombre",
          "engineer_of_record.registration": "Ingeniero responsable: matrícula", "engineer_of_record.college": "Ingeniero responsable: colegio",
          "language": "Idioma", "id": "Id", "name": "Nombre", "plan": "Plano", "description": "Descripción", "area": "Área", "kind": "Tipo de carga",
          "power.value": "Potencia: valor", "power.unit": "Potencia: unidad", "phases": "Fases", "length.value": "Longitud: valor", "length.unit": "Longitud: unidad",
          "text": "Texto del requisito", "source": "Origen", "status": "Estado"}


def walk_schema(node, path, required_chain, out):
    """Leaf fields of a JSON schema object as [(dotted path, sub schema, required, parent node, parent path)]."""
    required = set(node.get("required", []))
    for name, sub in node.get("properties", {}).items():
        p = path + [name]
        req = required_chain and name in required
        if sub.get("type") == "object":
            walk_schema(sub, p, req, out)
        else:
            out.append((".".join(p), sub, req, node, ".".join(path)))
    return out


def type_text(sub) -> str:
    t = sub.get("type")
    if "enum" in sub:
        return "lista cerrada"
    return {"string": "texto", "number": "número", "integer": "entero", "array": "lista de textos (separar con ;)"}.get(t, str(t))


def allowed_text(sub) -> str:
    parts = []
    if "enum" in sub:
        parts.append(" | ".join(str(x) for x in sub["enum"]))
    if "pattern" in sub:
        parts.append(f"formato {sub['pattern']}")
    if "exclusiveMinimum" in sub:
        parts.append(f"mayor que {sub['exclusiveMinimum']}")
    return "; ".join(parts)


def unit_text(name, parent) -> str:
    unit = parent.get("properties", {}).get("unit", {}).get("enum", [])
    return str(unit[0]) if name.endswith(".value") and len(unit) == 1 else ""


def description_text(path, sub, parent, parent_path) -> str:
    if sub.get("description"):
        return sub["description"]
    if path.endswith(".unit"):
        return f"Unidad de {parent_path}."
    return parent.get("description") or "(sin descripción en el esquema)"


def profile_sheet(ws, schema):
    fields = walk_schema(schema, [], True, [])
    headers = ["Campo", "Nombre", "Descripción (del esquema)", "Tipo", "Opciones o formato", "Unidad", "Obligatorio", "Valor"]
    style_header(ws, 1, headers, owner_from=len(headers))
    set_widths(ws, [34, 34, 60, 22, 30, 9, 12, 28])
    for r, (path, sub, req, parent, parent_path) in enumerate(fields, start=2):
        values = [path, LABELS.get(path, path), description_text(path, sub, parent, parent_path), type_text(sub), allowed_text(sub), unit_text(path, parent),
                  "Sí" if req else "No"]
        for c, v in enumerate(values, start=1):
            cell = put(ws, r, c, v)
            cell.alignment = WRAP
            cell.fill = LOCKED_FILL
        ws.cell(row=r, column=len(headers)).fill = OWNER_FILL
        if "enum" in sub:
            add_list(ws, [str(x) for x in sub["enum"]], f"H{r}")
    ws.freeze_panes = "B2"


def table_sheet(ws, item_schema, rows, lists=None):
    """A sheet of empty rows whose columns are the leaf fields of `item_schema`; enum fields get a drop-down list."""
    fields = walk_schema(item_schema, [], True, [])
    headers = [f"{LABELS.get(p, p)}{' *' if req else ''} ({p})" for p, _, req, _, _ in fields]
    style_header(ws, 1, headers, owner_from=1)
    set_widths(ws, [30] * len(headers))
    for c, (path, sub, _, _, _) in enumerate(fields, start=1):
        letter = get_column_letter(c)
        for r in range(2, rows + 2):
            ws.cell(row=r, column=c).fill = OWNER_FILL
        if lists and path in lists:
            add_list(ws, [], f"{letter}2:{letter}{rows + 1}", formula=lists[path])
        elif "enum" in sub:
            add_list(ws, [str(x) for x in sub["enum"]], f"{letter}2:{letter}{rows + 1}")
    ws.freeze_panes = "A2"
    return headers


def source_keys() -> str:
    return STAGES_SRC.read_text(encoding="utf-8")


def reference_sheet(ws):
    style_header(ws, 1, REF_HEADERS, owner_from=5)
    set_widths(ws, REF_WIDTHS)
    src = source_keys()
    rows = []
    for stage, key, name, unit, concept in REFERENCE_QUANTITIES:
        if f'"{key}"' not in src:
            raise SystemExit(f"output key {key!r} is not in {STAGES_SRC.name}: update REFERENCE_QUANTITIES")
        rows.append((stage, concept, name, unit))
    rows += [(stage, concept, name, unit) for stage, name, unit, concept in BOQ_QUANTITIES]
    for r, values in enumerate(rows, start=2):
        for c, v in enumerate(values, start=1):
            cell = put(ws, r, c, v)
            cell.alignment = WRAP
            cell.fill = LOCKED_FILL
        for c in range(5, 9):
            ws.cell(row=r, column=c).fill = OWNER_FILL
    ws.freeze_panes = "A2"


def tolerance_sheet(ws):
    ws.column_dimensions["A"].width = 70
    ws.column_dimensions["B"].width = 30
    style_header(ws, 1, ["Decisión del dueño", "Valor"], owner_from=2)
    r = 2
    for title, items in TOLERANCES:
        put(ws, r, 1, title).font = Font(bold=True)
        r += 1
        for label, _ in items:
            put(ws, r, 1, label).alignment = WRAP
            ws.cell(row=r, column=2).fill = OWNER_FILL
            r += 1
        r += 1


def build_spike() -> Workbook:
    schemas = {name: N.load_json(P.SCHEMAS / f"{name}.schema.json") for name in ("intake_answers", "load_list", "requirements")}
    wb = Workbook()
    text_sheet(wb.active, INSTRUCTIONS_SPIKE)
    wb.active.title = "Instrucciones"
    profile_sheet(wb.create_sheet("Perfil"), schemas["intake_answers"])
    load = schemas["load_list"]["properties"]
    table_sheet(wb.create_sheet("Áreas"), load["areas"]["items"], BLANK_ROWS["Áreas"])
    table_sheet(wb.create_sheet("Cargas"), load["loads"]["items"], BLANK_ROWS["Cargas"], lists={"area": "='Áreas'!$A$2:$A$" + str(BLANK_ROWS["Áreas"] + 1)})
    table_sheet(wb.create_sheet("Requisitos"), schemas["requirements"]["properties"]["items"]["items"], BLANK_ROWS["Requisitos"])
    reference_sheet(wb.create_sheet("Valores de referencia"))
    tolerance_sheet(wb.create_sheet("Tolerancias"))
    return finish(wb)


# ------------------------------------------------------------------ writing and checking
def snapshot(wb) -> dict:
    """The content of a workbook that matters: cells (values and formulas), lists, freeze panes, filter, widths."""
    out = {"creator": wb.properties.creator, "sheets": {}}
    for ws in wb.worksheets:
        out["sheets"][ws.title] = {
            "freeze": ws.freeze_panes, "filter": ws.auto_filter.ref,
            "widths": {k: round(d.width or 0, 1) for k, d in sorted(ws.column_dimensions.items())},
            "lists": sorted((dv.type, dv.formula1, str(dv.sqref)) for dv in ws.data_validations.dataValidation),
            "cells": {c.coordinate: c.value for row in ws.iter_rows() for c in row if c.value is not None}}
    return out


def roundtrip(wb) -> Workbook:
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return load_workbook(buf)


def builders(reg) -> dict:
    return {WORKSHEET: lambda: build_worksheet(reg), SPIKE: build_spike}


def differences(expected: dict, found: dict, label: str) -> list:
    """Short messages about what differs between two snapshots."""
    out = []
    for sheet in sorted(set(expected["sheets"]) | set(found["sheets"])):
        a, b = expected["sheets"].get(sheet), found["sheets"].get(sheet)
        if a is None or b is None:
            out.append(f"{label}: sheet {sheet!r} {'missing on disk' if b is None else 'not expected'}")
            continue
        for key in ("freeze", "filter", "widths", "lists"):
            if a[key] != b[key]:
                out.append(f"{label}/{sheet}: {key} differs")
        bad = sorted(c for c in set(a["cells"]) | set(b["cells"]) if a["cells"].get(c) != b["cells"].get(c))
        out += [f"{label}/{sheet}!{c}: expected {a['cells'].get(c)!r:.60}, found {b['cells'].get(c)!r:.60}" for c in bad[:5]]
        if len(bad) > 5:
            out.append(f"{label}/{sheet}: {len(bad)} cells differ")
    if expected["creator"] != found["creator"]:
        out.append(f"{label}: workbook properties differ")
    return out


def check(reg, folder: Path) -> list:
    problems = []
    for name, build in builders(reg).items():
        path = folder / name
        if not path.is_file():
            problems.append(f"{name}: missing in {folder}")
            continue
        problems += differences(snapshot(roundtrip(build())), snapshot(load_workbook(path)), name)
    return problems


def write_all(reg, folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    for name, build in builders(reg).items():
        build().save(folder / name)
        print(f"wrote {folder / name}")


def summary(reg) -> str:
    rows = ordered_rows(reg)
    counts = [sum(1 for g, _ in rows if g == n) for n in range(1, len(GROUPS) + 1)]
    return "worksheet rows: " + ", ".join(f"{g}: {c}" for g, c in zip(GROUPS, counts)) + f" (total {len(rows)})"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 when the files on disk are out of date")
    ap.add_argument("--out", default=str(OUT_DIR), help="output folder (tests use a temp dir)")
    args = ap.parse_args(argv)
    reg = N.Register(N.REPO)
    if reg.errors:
        print("the norm register has errors; fix them first:\n  " + "\n  ".join(reg.errors[:5]))
        return 1
    print(summary(reg))
    if args.check:
        problems = check(reg, Path(args.out))
        for p in problems:
            print("STALE", p)
        if problems:
            print("run `python harness/tools/build/validation_templates.py` to regenerate")
        return 1 if problems else 0
    write_all(reg, Path(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
