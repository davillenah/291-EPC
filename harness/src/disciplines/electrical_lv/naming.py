"""Names of the issued files (PROPOSAL: folder structure and nomenclature). Pure: it builds and checks names and writes nothing.

Code of a document: `<project_code>-<DISC>-<SUB>-<TYPE>-<NNN>[-<LEVEL>]`, for example `2026-ES-HNDA-3085-E-LV-SLD-001-L01`.
  DISC   `E` (electrical); SUB `LV` or `MV`; the system (lighting, receptacles...) goes into the description, not into the code.
  TYPE   the three letters of `document-catalog.json` (plus SEC, ELV and DET for sections, elevations and details).
  NNN    counts the documents of that type in the project (SLD-001 is the general single-line diagram, SLD-002 the lighting one...).
  LEVEL  only for a document that belongs to one level: `L00` ground floor, `L01`.. above, `LS01`.. below ground (two digits).
File name: `<code>_<description>.<ext>`. The description is English, lower case, full words joined by `_`, at most 40 characters, specific to the content of
the document (not to its type) and never changed once issued. No revision and no transmittal number goes into the name: they live in the manifest, in the
transmittal and inside the file.
Plans and diagrams (SLD, MLD, PLN, SEC, ELV, DET) always sit in a folder `<code>_<description>/` with one file per page, `<code>_<description>_P01.dxf`, `_P02`...;
single-piece documents (CAL, RPT, LST, SPC, ANL, SCH, TAB, CIR) are loose files.
In the transmittal each of them sits in a numbered kind folder (`01_SLD`, `02_MLD`, `04_PLANS`, `06_DOCUMENTS`...; see `stages/package_stage.py`).

The names are given by a person in the engine inputs (`deliverable_names`, keyed by the name the engine uses); nothing here invents a description.
"""
import re

DISCIPLINE = "E"
SUBDISCIPLINES = ("LV", "MV")
TYPES = ("ANL", "CAL", "CIR", "DET", "ELV", "LST", "MLD", "PLN", "RPT", "SCH", "SEC", "SLD", "SPC", "TAB")
PAGED_TYPES = ("DET", "ELV", "MLD", "PLN", "SEC", "SLD")
MAX_DESCRIPTION = 40
PATH_WARNING = 240                      # characters; Windows stops at about 260
PROJECT_CODE = re.compile(r"[0-9]{4}-[A-Z]{2,4}-[A-Z]{2,4}-[A-Z0-9]{3,6}")
DESCRIPTION = re.compile(r"[a-z0-9]+(_[a-z0-9]+)*")
LEVEL = re.compile(r"L(S?)[0-9]{2}")
KEYS = ("type", "number", "description", "level", "page", "sub")


def _whole(value, low, high):
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def _checks(entry):
    """(is valid, message) of each field of a naming entry, in the order they are reported."""
    text, level = entry.get("description"), entry.get("level")
    return [
        (entry.get("type") in TYPES, f"type {entry.get('type')!r} must be one of {', '.join(TYPES)}"),
        (_whole(entry.get("number"), 1, 999), "number must be a whole number from 1 to 999"),
        (isinstance(text, str) and bool(DESCRIPTION.fullmatch(text)) and len(text) <= MAX_DESCRIPTION,
         f"description must be lower case English words joined by _ (at most {MAX_DESCRIPTION} characters)"),
        (level is None or (isinstance(level, str) and bool(LEVEL.fullmatch(level))), "level must look like L00, L01 (above ground) or LS01 (below ground)"),
        (_whole(entry.get("page", 1), 1, 99), "page must be a whole number from 1 to 99"),
        (entry.get("sub", SUBDISCIPLINES[0]) in SUBDISCIPLINES, f"sub must be one of {', '.join(SUBDISCIPLINES)}"),
    ]


def problems(entry):
    """Reasons a naming entry is not valid (empty list = valid)."""
    if not isinstance(entry, dict):
        return ["the naming entry must be an object"]
    return [f"unknown key {k!r}" for k in sorted(set(entry) - set(KEYS))] + [message for good, message in _checks(entry) if not good]


def document_code(project_code, entry):
    """`2026-ES-HNDA-3085-E-LV-SLD-001[-L01]` of a valid naming entry."""
    parts = [project_code, DISCIPLINE, entry.get("sub", SUBDISCIPLINES[0]), entry["type"], f"{entry['number']:03d}"]
    return "-".join(parts + ([entry["level"]] if entry.get("level") else []))


def stem(project_code, entry):
    return f"{document_code(project_code, entry)}_{entry['description']}"


def file_path(project_code, entry, extension, in_type_folder=False):
    """Path of a file inside its transmittal folder: `<stem><ext>` or `<stem>/<stem>_P01<ext>` for plans and diagrams (`<stem>_P01<ext>` when the file already sits in the folder of its kind, `drawings/sld`)."""
    name = stem(project_code, entry)
    if entry["type"] in PAGED_TYPES and in_type_folder:
        return f"{name}_P{entry.get('page', 1):02d}{extension}"
    if entry["type"] in PAGED_TYPES:
        return f"{name}/{name}_P{entry.get('page', 1):02d}{extension}"
    return f"{name}{extension}"


# ---- automatic names (SIM-10): a project that gives no `deliverable_names` still gets the code and the file names of its deliverables --------------------------------------------------
# Catalogue of the documents the stages produce: engine name -> (type, description). A fixed table of English words, not an invention per project; a project that wants other names gives `deliverable_names`.
DOCUMENT_CATALOGUE = {
    "calculation_memo": ("CAL", "feeder_sizing_calculation"), "raceway_memo": ("CAL", "raceway_sizing_calculation"), "short_circuit_study": ("ANL", "short_circuit_study"),
    "selectivity_study": ("ANL", "selectivity_study"), "lighting_study": ("ANL", "lighting_study"), "descriptive_report": ("RPT", "descriptive_report"), "design_basis": ("RPT", "design_basis"),
    "project_summary": ("RPT", "project_summary"), "load_schedule": ("LST", "load_schedule"), "terminal_block_list": ("LST", "terminal_block_list"), "boq": ("LST", "bill_of_quantities"),
    "cable_list": ("CIR", "cable_list"), "specification": ("SPC", "technical_specification"), "rfq": ("SPC", "request_for_quotation"), "datasheets": ("SCH", "datasheets"),
}
FORMAT_SUFFIX = re.compile(r"_(pdf|docx|xlsx)$")
_SHEET = re.compile(r"_H([0-9]+)$")


def _drawing_kind(name):
    """(type, description, level id or None) of a drawing by its engine name: `SLD_X_H1`, `MLD_X_H1`, `X_plan_PB[_sheet]`, `X_lighting_PB[_sheet]`, `X_model_3d`, `X_section_A`."""
    for prefix, kind, text in (("SLD_", "SLD", "single_line_diagram"), ("MLD_", "MLD", "board_layout")):
        if name.startswith(prefix):
            return kind, text, None
    plan = re.search(r"_(plan|lighting)_([A-Za-z0-9]+?)(_sheet)?$", name)
    if plan:
        return "PLN", f"{'electrical' if plan.group(1) == 'plan' else 'lighting'}_plan{'_sheet' if plan.group(3) else ''}", plan.group(2)
    section = re.search(r"_section_([A-Za-z0-9]+)$", name)
    if section:
        return "SEC", f"section_{section.group(1).lower()}", None
    return ("PLN", "model_3d", None) if name.endswith("_model_3d") else ("DET", re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:MAX_DESCRIPTION], None)


def _level_code(floor_id, floors):
    """`L00`, `L01`... for a floor id by the order of the levels (`elevation_m`, else the order given); `LS01`.. when it is below ground."""
    order = sorted(floors, key=lambda f: (f.get("elevation_m") or 0))
    ids = [f["id"] for f in order]
    if floor_id not in ids:
        return None
    below = [f["id"] for f in order if (f.get("elevation_m") or 0) < 0]
    if floor_id in below:
        return f"LS{len(below) - below.index(floor_id):02d}"
    return f"L{ids.index(floor_id) - len(below):02d}"


def _classify(name, floors):
    """(type, description, level, page, group) of an engine name; the table sheet of a diagram gets page 100 (renumbered after the sheets)."""
    base = FORMAT_SUFFIX.sub("", name)
    if base in DOCUMENT_CATALOGUE:
        return DOCUMENT_CATALOGUE[base] + (None, 1, base)
    if name.endswith("_tables_xlsx"):
        return "TAB", "document_tables", None, 1, "tables"
    kind, text, floor = _drawing_kind(base)
    sheet = _SHEET.search(base)
    group = base[:sheet.start()] if sheet else base.removesuffix("_TABLA")
    page = int(sheet.group(1)) if sheet else (100 if base.endswith("_TABLA") else 1)
    return kind, text, (_level_code(floor, floors) if floor else None), page, group


def automatic(names, floors=()):
    """{engine name: naming entry} for the engine names `names` (drawings and files of documents), numbered per type by name order; the sheets of one diagram are pages of one document."""
    out, numbers = {}, {}
    for name in sorted(names):
        kind, text, level, page, group = _classify(name, floors)
        numbers.setdefault((kind, group), 1 + sum(1 for k in numbers if k[0] == kind))
        entry = {"type": kind, "number": numbers[(kind, group)], "description": text[:MAX_DESCRIPTION]}
        entry.update({"level": level} if level else {})
        entry.update({"page": page} if kind in PAGED_TYPES else {})
        out[name] = entry
    return _compact_pages(out)


def _compact_pages(entries):
    """Pages as 1, 2, 3 within one document (the table sheet, numbered 100+ while the sheets are sorted, goes last)."""
    docs = {}
    for name, e in entries.items():
        if "page" in e:
            docs.setdefault((e["type"], e["number"]), []).append(name)
    for members in docs.values():
        for n, name in enumerate(sorted(members, key=lambda m: (entries[m]["page"], m)), start=1):
            entries[name]["page"] = n
    return entries
