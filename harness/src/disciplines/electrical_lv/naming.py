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


def problems(entry):
    """Reasons a naming entry is not valid (empty list = valid)."""
    if not isinstance(entry, dict):
        return ["the naming entry must be an object"]
    out = [f"unknown key {k!r}" for k in sorted(set(entry) - set(KEYS))]
    if entry.get("type") not in TYPES:
        out.append(f"type {entry.get('type')!r} must be one of {', '.join(TYPES)}")
    number = entry.get("number")
    if not (isinstance(number, int) and not isinstance(number, bool) and 1 <= number <= 999):
        out.append("number must be a whole number from 1 to 999")
    text = entry.get("description")
    if not (isinstance(text, str) and DESCRIPTION.fullmatch(text) and len(text) <= MAX_DESCRIPTION):
        out.append(f"description must be lower case English words joined by _ (at most {MAX_DESCRIPTION} characters)")
    if entry.get("level") is not None and not (isinstance(entry["level"], str) and LEVEL.fullmatch(entry["level"])):
        out.append("level must look like L00, L01 (above ground) or LS01 (below ground)")
    page = entry.get("page", 1)
    if not (isinstance(page, int) and not isinstance(page, bool) and 1 <= page <= 99):
        out.append("page must be a whole number from 1 to 99")
    if entry.get("sub", SUBDISCIPLINES[0]) not in SUBDISCIPLINES:
        out.append(f"sub must be one of {', '.join(SUBDISCIPLINES)}")
    return out


def document_code(project_code, entry):
    """`2026-ES-HNDA-3085-E-LV-SLD-001[-L01]` of a valid naming entry."""
    parts = [project_code, DISCIPLINE, entry.get("sub", SUBDISCIPLINES[0]), entry["type"], f"{entry['number']:03d}"]
    return "-".join(parts + ([entry["level"]] if entry.get("level") else []))


def stem(project_code, entry):
    return f"{document_code(project_code, entry)}_{entry['description']}"


def file_path(project_code, entry, extension):
    """Path of a file inside its transmittal folder: `<stem><ext>` or `<stem>/<stem>_P01<ext>` for plans and diagrams."""
    name = stem(project_code, entry)
    if entry["type"] in PAGED_TYPES:
        return f"{name}/{name}_P{entry.get('page', 1):02d}{extension}"
    return f"{name}{extension}"
