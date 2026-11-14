"""Files for the documents of stage 11: PDF and Word (the report renderers of the drawing engine) and an Excel workbook of the tables.

The discipline writes no text of its own here: it converts the structured document (the memo and summary of the engine already are reports; the documents with sections of blocks or of items are
laid out as headings, paragraphs, bullets and tables) into the report structure `epc_drawing.export.report_pdf` and `report_docx` take, and hands it to them. The tables of a document go to one sheet each
of a workbook (`openpyxl`). A document with a structure of its own (terminal list, bill of quantities, datasheets, RFQ, lighting study) is not rendered: it stays a structured document and is
listed in `not_rendered`.

  formats   `engine_inputs["documents"]["formats"]` (a subset of pdf, docx, xlsx); a building run (stage 3 routed the floors) renders pdf and docx and the workbook of the documents with tables.
"""
import hashlib
from pathlib import Path

from disciplines.electrical_lv.stages import engine_calls as EC

FORMATS = ("pdf", "docx", "xlsx")
BUILDING_FORMATS = ("pdf", "docx", "xlsx")
ENGINE = "cad/drawing"
FUNCTIONS = {"pdf": "epc_drawing.export.report_pdf.render", "docx": "epc_drawing.export.report_docx.render"}
PAGE_LABEL = "Page {n} of {total}"


def formats_of(context):
    """The formats to write: the ones `engine_inputs["documents"]["formats"]` lists, or all of them on a building run, else none."""
    given = (EC.inputs_of(context).get("documents") or {}).get("formats")
    if given is not None:
        bad = [f for f in given if f not in FORMATS]
        if bad or not isinstance(given, list):
            raise ValueError(f"engine_inputs.documents.formats: {bad or given!r} is not a list of {', '.join(FORMATS)}")
        return tuple(given)
    return BUILDING_FORMATS if EC.inputs_of(context).get("routing") else ()


def _cell(value):
    return "" if value is None else str(value)


def _table(columns, rows):
    width = 1.0 / max(len(columns), 1)
    return {"type": "table", "columns": [(str(c), width) for c in columns], "rows": [[_cell(v) for v in r] for r in rows]}


def _block(b):
    """One block of a structured document as a block of the report."""
    kind = b["type"]
    if kind == "paragraph":
        return [{"type": "p", "text": b["text"]}]
    if kind == "list":
        return [{"type": "bullets", "items": [str(i) for i in b["items"]]}]
    if kind == "table":
        return [_table(b["columns"], b["rows"])]
    return [{"type": "p", "text": f"{b['text']} ({b['who']})"}]


def _items_table(items):
    return _table(["item", "value", "unit", "source"], [(i.get("label") or i.get("key"), i.get("value"), i.get("unit"), i.get("source")) for i in items])


def _section(s):
    blocks = [{"type": "h", "text": f"{s['id']}. {s['title']}" if s["id"].isdigit() else s["title"]}]
    if "blocks" in s:
        return blocks + [out for b in s["blocks"] for out in _block(b)]
    return blocks + ([_items_table(s["items"])] if s.get("items") else [])


CABLE_COLUMNS = ("circuit", "from", "to", "phases", "material", "insulation", "s_mm2", "neutral_mm2", "pe_mm2", "method", "length_m", "ib_a", "in_a", "du_pct", "compliant")


def _cable_list_report(document, project):
    """The cable list as a report: one table, a row per sized circuit (the room and runs of a routed circuit in the last column)."""
    rows = [[r.get(c) for c in CABLE_COLUMNS] + [", ".join(k["tag"] for k in (r.get("raceway") or {}).get("containers", []))] for r in document["rows"]]
    return {"title": "Cable list", "subtitle": project, "footer": f"Cable list - {project}", "page_label": PAGE_LABEL,
            "blocks": [{"type": "h", "text": document["board"]}, _table(list(CABLE_COLUMNS) + ["runs"], rows)]}


def _has_sections(document):
    """Whether a document is a list of sections whose parts are blocks or items (the structure `_section` lays out)."""
    sections = document.get("sections")
    return isinstance(sections, list) and all(isinstance(x, dict) and ("blocks" in x or "items" in x) for x in sections)


def to_report(name, document, project):
    """The report structure of a document, or None when its structure is its own (not rendered)."""
    if name == "cable_list":
        return _cable_list_report(document, project)
    if "blocks" in document and "title" in document:
        return dict(document)
    if not _has_sections(document):
        return None
    title = document.get("title") or name.replace("_", " ").capitalize()
    return {"title": title, "subtitle": project, "footer": f"{title} - {project}", "page_label": PAGE_LABEL, "blocks": [b for s in document["sections"] for b in _section(s)]}


def _tables(report):
    return [b for b in report["blocks"] if b["type"] == "table"]


def _sheets(reports):
    """[(sheet name, columns, rows)] of every table of the reports, the sheet named `<document>-<n>`."""
    return [(f"{name}-{n}", [c for c, _ in t["columns"]], t["rows"]) for name, report in reports for n, t in enumerate(_tables(report), start=1)]


def _entry(path, root):
    data = Path(path).read_bytes()
    return {"name": Path(path).stem + "_" + Path(path).suffix.lstrip("."), "path": Path(path).relative_to(root).as_posix(), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _render_one(name, report, out_dir, formats):
    """The files of one document in the formats asked (the report renderers of the drawing engine)."""
    from epc_drawing.export import report_docx, report_pdf
    done = []
    if "pdf" in formats:
        done.append(_entry(report_pdf.render(report, out_dir / f"{name}.pdf"), out_dir.parent))
    if "docx" in formats:
        done.append(_entry(report_docx.render(report, out_dir / f"{name}.docx"), out_dir.parent))
    return done


def _reports(docs, project):
    """([(name, report)] of the documents that have a report structure, [names of the ones that do not])."""
    every = [(name, to_report(name, document, project)) for name, document in docs.items()]
    return [(n, r) for n, r in every if r is not None], [n for n, r in every if r is None]


def render_all(docs, project, out_dir, formats):
    """Writes the files of the documents under `out_dir`; returns ({"files": [...], "not_rendered": [...]}, engine calls)."""
    from epc_drawing.export import tables_xlsx
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    reports, skipped = _reports(docs, project)
    files = [f for name, report in reports for f in _render_one(name, report, out_dir, formats)]
    book = out_dir / f"{project or 'documents'}_tables.xlsx"
    if "xlsx" in formats and tables_xlsx.write_tables(book, _sheets(reports)):
        files.append(_entry(book, out_dir.parent))
    return {"files": files, "not_rendered": skipped}, [EC.record_for(ENGINE, FUNCTIONS[f]) for f in ("pdf", "docx") if f in formats]
