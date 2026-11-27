"""Files for the documents of stage 11: PDF and Word (the report renderers of the drawing engine) and an Excel workbook of the tables.

The discipline writes no text of its own here: it converts the structured document (the memo and summary of the engine already are reports; the documents with sections of blocks or of items are
laid out as headings, paragraphs, bullets and tables) into the report structure `epc_drawing.export.report_pdf` and `report_docx` take, and hands it to them. The tables of a document go to one sheet each
of a workbook (`openpyxl`). The terminal list, the bill of quantities, the datasheets, the RFQ and the lighting study have a layout of their own here (SIM-19); a document whose structure is unknown stays structured and is listed in `not_rendered`.
Language: with a project in Spanish the descriptive report is the Spanish text of its engine and the platform's own words (titles, generic columns, page label) are Spanish (SIM-14).

  formats   `engine_inputs["documents"]["formats"]` (a subset of pdf, docx, xlsx); a building run (stage 3 routed the floors) renders pdf and docx and the workbook of the documents with tables.
"""
import hashlib
from pathlib import Path

from disciplines.electrical_lv import lux_map

from disciplines.electrical_lv.stages import engine_calls as EC

FORMATS = ("pdf", "docx", "xlsx")
BUILDING_FORMATS = ("pdf", "docx", "xlsx")
PV_FORMATS = ("pdf", "docx")
ENGINE = "cad/drawing"
FUNCTIONS = {"pdf": "epc_drawing.export.report_pdf.render", "docx": "epc_drawing.export.report_docx.render"}
PAGE_LABEL = "Page {n} of {total}"      # the same text as `epc_report.core.blocks.PAGE_LABEL`; engines are imported when used, so the permission hook (standard library only) can load this module
EDIT_MARK = "EDIT MODE: norm values not verified, not for production"
EDIT_MARK_ES = "MODO EDICIÓN: valores de norma sin verificar, no apto para producción"


def formats_of(context):
    """The formats to write: the ones `engine_inputs["documents"]["formats"]` lists, all of them on a building run, PDF and Word on a PV run (PV-16), else none."""
    given = (EC.inputs_of(context).get("documents") or {}).get("formats")
    if given is not None:
        bad = [f for f in given if f not in FORMATS]
        if bad or not isinstance(given, list):
            raise ValueError(f"engine_inputs.documents.formats: {bad or given!r} is not a list of {', '.join(FORMATS)}")
        return tuple(given)
    if EC.inputs_of(context).get("routing"):
        return BUILDING_FORMATS
    return PV_FORMATS if EC.inputs_of(context).get("pv") else ()


def _cell(value):
    from epc_report.core import blocks
    return blocks.cell(value)


def _table(columns, rows):
    from epc_report.core import blocks
    return blocks.table(columns, rows)


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


def _notes(document):
    from epc_report.core import blocks
    return blocks.notes(document)


def _terminal_block_report(d, project):
    rows = [[r["circuit"], r.get("description"), r.get("device"), r.get("in_a"), r.get("phases"), r.get("conductors"), ", ".join(t["id"] for t in r["terminals"][:1] + r["terminals"][-1:])]
            for strip in d["strips"] for r in strip["rows"]]
    totals = [[k, v] for k, v in d["totals"]["by_section"].items()]
    return {"title": "Terminal block list", "subtitle": project, "footer": f"Terminal block list - {project}", "page_label": PAGE_LABEL,
            "blocks": [{"type": "h", "text": d["board"]}, _table(["circuit", "description", "device", "in_a", "phases", "conductors", "terminals (first, last)"], rows),
                       {"type": "p", "text": f"Terminals in total: {d['totals']['terminals']}."}, _table(["section (mm2)", "terminals"], totals)] + _notes(d)}


def _readings(result, language):
    """The table of the lux readings of the rooms that have a map: required, lumen-method average, direct-light minimum / average / maximum, uniformity and whether it complies."""
    maps = [m for m in (lux_map.room_map(x) for x in result["rooms"]) if m]
    return [[m["name"] or m["id"], m["target_lux"], m["average_lux"], f"{m['stats']['min_lux']:g} / {m['stats']['avg_lux']:g} / {m['stats']['max_lux']:g}", m["stats"]["min_over_avg"],
             lux_map.say("yes" if m["complies"] else "no", language)] for m in maps]


def _lighting_report(d, project, language="en"):
    rows = [[r["id"], r.get("name"), (r.get("luminaire") or {}).get("name"), (r.get("target") or {}).get("value"), (r.get("flux") or {}).get("luminaires_required"), (r.get("layout") or {}).get("installed")]
            for r in d["result"]["rooms"]]
    counts = d["result"]["counts"]
    blocks = [{"type": "p", "text": f"Rooms: {counts['rooms']}; luminaires: {counts['luminaires']}; warnings: {counts['warnings']}. Engine {d['engine']['name']} {d['engine']['version']}."},
              _table(["room", "name", "luminaire", "target (lx)", "required", "installed"], rows)]
    readings = _readings(d["result"], language)
    blocks += [_table(lux_map.TEXT["columns"]["es" if language == "es" else "en"], readings)] if readings else []
    return {"title": "Lighting study", "subtitle": project, "footer": f"Lighting study - {project}", "page_label": PAGE_LABEL,
            "blocks": blocks + lux_map.study_blocks(d["result"], language) + _notes({"issues": d["result"].get("warnings")})}


def _pv_weight_of(result):
    """The weight of one module of the format record (`epc_pv.equipment.module_weight_kg`), or None; the report engine reads no record, so the discipline looks it up."""
    from epc_pv import equipment
    dims = ((result.get("layout") or {}).get("module") or {}).get("dimensions_mm")
    return equipment.module_weight_kg(dims) if dims else None


def _pv_equipment_blocks(result):
    from epc_report.pv import yield_study as pv_yield_study
    return pv_yield_study.equipment_blocks(result, _pv_weight_of(result))


def _pv_fill_blocks(result):
    from epc_report.pv import yield_study as pv_yield_study
    return pv_yield_study.fill_blocks(result)


def _pv_report(d, project):
    from epc_report.pv import yield_study as pv_yield_study
    return pv_yield_study.pv_yield_report(d, project, _pv_weight_of(d["result"]))


PV_TEXT_REPORTS = ("pv_calc_memo", "pv_summary", "pv_descriptive_report", "pv_savings_memo", "pv_economic_memo", "pv_savings_descriptive", "pv_economic_descriptive")


def _pv_text_report(name, d, project, language):
    """The PV documents written by the report engine in English or Spanish: the engine result, the engine input and the one-line problem the person gave are all it gets."""
    from epc_report.pv import calc_memo, economics, narrative, summary
    from epc_report.pv.texts import tr
    lang = "es" if language == "es" else "en"
    problem = d.get("problem")
    builders = {"pv_calc_memo": lambda: calc_memo.pv_calc_memo(d, d.get("inputs") or {}, project, lang),
                "pv_summary": lambda: summary.pv_summary(d, d.get("inputs") or {}, project, problem or tr(lang, "n_a"), lang),
                "pv_descriptive_report": lambda: narrative.pv_descriptive_report(d, project, problem, lang),
                "pv_savings_memo": lambda: economics.pv_savings_memo(d, project, lang),
                "pv_economic_memo": lambda: economics.pv_economic_memo(d, project, lang),
                "pv_savings_descriptive": lambda: narrative.pv_savings_descriptive(d, project, problem, lang),
                "pv_economic_descriptive": lambda: narrative.pv_economic_descriptive(d, project, problem, lang)}
    return builders[name]()


def _boq_report(d, project):
    rows = [[i["item_id"], i["category"], i["description"], i["unit"], i["quantity"]] for i in d["items"]]
    totals = d["totals"]
    return {"title": "Bill of quantities", "subtitle": project, "footer": f"Bill of quantities - {project}", "page_label": PAGE_LABEL,
            "blocks": [{"type": "h", "text": d["board"]}, {"type": "p", "text": f"Lines: {totals['lines']}; cable: {totals['cable_m']} m; devices: {totals['devices']}. Wastage allowance: {d['allowance_pct']} %."},
                       _table(["item", "category", "description", "unit", "quantity"], rows)] + _notes(d)}


def _datasheets_report(d, project):
    rows = [[i["item_id"], i["kind"], len(i["candidates"]), i["review_status"]] for i in d["datasheets"]]
    return {"title": "Datasheets", "subtitle": project, "footer": f"Datasheets - {project}", "page_label": PAGE_LABEL,
            "blocks": [{"type": "h", "text": d["board"]}, {"type": "p", "text": f"Items: {d['totals']['items']}; without a catalog candidate: {d['totals']['items_without_candidate']}."},
                       _table(["item", "kind", "candidates", "review"], rows)] + _notes(d)}


def _rfq_report(d, project):
    terms = [[k, "" if v is None else v] for k, v in d["terms"].items()]
    suppliers = [[s["name"], s.get("contact")] for s in d["issued_for"]]
    rows = [[ln["line_no"], ln["item_id"], ln["description"], ln["unit"], ln["quantity"]] for ln in d["lines"]]
    return {"title": "Request for quotation", "subtitle": project, "footer": f"Request for quotation - {project}", "page_label": PAGE_LABEL,
            "blocks": [{"type": "h", "text": d["rfq_id"]}, _table(["term", "value"], terms), {"type": "h", "text": "Suppliers"}, _table(["supplier", "contact"], suppliers),
                       {"type": "h", "text": "Lines"}, _table(["line", "item", "description", "unit", "quantity"], rows)] + _notes(d)}


OWN_REPORTS = {"terminal_block_list": _terminal_block_report, "lighting_study": _lighting_report, "pv_yield_study": _pv_report, "boq": _boq_report, "datasheets": _datasheets_report, "rfq": _rfq_report}


def _has_sections(document):
    """Whether a document is a list of sections whose parts are blocks or items (the structure `_section` lays out)."""
    sections = document.get("sections")
    return isinstance(sections, list) and all(isinstance(x, dict) and ("blocks" in x or "items" in x) for x in sections)


def marked(report, mode, language="en"):
    """The report with the mark of the edit mode in its footer (a production report is returned as it is)."""
    if report is None or mode != "edit":
        return report
    return dict(report, footer=(f"{report['footer']} - " if report.get("footer") else "") + (EDIT_MARK_ES if language == "es" else EDIT_MARK))


# Spanish for the words the platform itself puts in a document (SIM-14): titles and the columns of the generic tables. The engines that write Spanish already (the memo, the summary) are not touched.
ES_TITLES = {"Terminal block list": "Lista de borneras", "Lighting study": "Estudio de iluminación", "PV yield study": "Estudio de producción fotovoltaica", "Bill of quantities": "Cómputo de materiales", "Datasheets": "Hojas de datos",
             "Request for quotation": "Pedido de cotización", "Cable list": "Lista de cables", "Descriptive report": "Memoria descriptiva", "Design basis": "Bases de diseño", "Load schedule": "Planilla de cargas",
             "Memo of cables and raceways": "Memoria de cables y canalizaciones", "Protection selectivity study": "Estudio de selectividad de protecciones",
             "Short-circuit study": "Estudio de cortocircuito", "Specification": "Pliego de especificaciones técnicas"}
ES_COLUMNS = {"item": "concepto", "value": "valor", "unit": "unidad", "source": "fuente", "circuit": "circuito", "description": "descripción", "device": "dispositivo", "phases": "fases",
              "conductors": "conductores", "category": "categoría", "quantity": "cantidad", "room": "ambiente", "name": "nombre", "luminaire": "luminaria", "required": "requeridas",
              "installed": "instaladas", "array": "arreglo", "modules": "módulos", "inverters": "inversores", "modules_in_series": "módulos en serie", "strings": "strings", "month": "mes", "ac_kwh": "energía AC (kWh)", "kwh_per_kwp": "kWh/kWp", "pr": "PR", "cf": "factor de capacidad", "kind": "tipo", "candidates": "candidatos", "review": "revisión", "term": "condición", "supplier": "proveedor", "contact": "contacto", "line": "línea"}
ES_PAGE_LABEL = "Página {n} de {total}"


def _descriptive_report_es(document, project):
    """The descriptive report in Spanish: the plain text of the engine (`epc_descriptive_report.descriptive_report_to_text`) laid out as headings, paragraphs and bullets."""
    import re
    import epc_descriptive_report
    blocks = []
    lines = epc_descriptive_report.descriptive_report_to_text(document).split("\n")
    title = lines[0]
    for chunk in "\n".join(lines[1:]).split("\n\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        first, _, rest = chunk.partition("\n")
        if re.fullmatch(r"\d+\. .+", first) or first == "Observaciones":
            blocks.append({"type": "h", "text": first})
            chunk = rest.strip()
        if chunk.startswith("- "):
            blocks.append({"type": "bullets", "items": [row[2:] for row in chunk.split("\n") if row.startswith("- ")]})
        elif chunk:
            blocks.append({"type": "p", "text": chunk})
    return {"title": title, "subtitle": project, "footer": f"{title} - {project}", "page_label": ES_PAGE_LABEL, "blocks": blocks}


def _in_spanish(report):
    """The report with the platform's own words in Spanish (title, generic column headings, page label)."""
    out = dict(report, title=ES_TITLES.get(report["title"], report["title"]), page_label=ES_PAGE_LABEL)
    out["footer"] = (report.get("footer") or "").replace(report["title"], out["title"], 1)
    out["blocks"] = [dict(b, columns=[(ES_COLUMNS.get(c, c), w) for c, w in b["columns"]]) if b["type"] == "table" else b for b in report["blocks"]]
    return out


def to_report(name, document, project, language="en"):
    """The report structure of a document, or None when its structure is its own (not rendered). `language` is the one of the project (`es` writes the platform's own words in Spanish)."""
    if name == "descriptive_report" and language == "es" and isinstance(document.get("sections"), list):
        return _descriptive_report_es(document, project)
    if name in PV_TEXT_REPORTS:
        return _pv_text_report(name, document, project, language)                     # the PV memorandum and summary come in English and Spanish from the report engine
    report = _lighting_report(document, project, language) if name == "lighting_study" else _to_report(name, document, project)
    return _in_spanish(report) if report is not None and language == "es" else report


def _to_report(name, document, project):
    if name in OWN_REPORTS:
        return OWN_REPORTS[name](document, project)
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


def _render_files(reports, out_dir, formats):
    """The files of every document, in the order of the documents (PDF then DOCX of each): the PDFs are drawn by several processes at once (OPT-06), the DOCX files here meanwhile."""
    from epc_drawing.export import report_docx, report_pdf
    pdfs = iter(report_pdf.render_many([(report, out_dir / f"{name}.pdf") for name, report in reports]) if "pdf" in formats else [])
    files = []
    for name, report in reports:
        if "pdf" in formats:
            files.append(_entry(next(pdfs), out_dir.parent))
        if "docx" in formats:
            files.append(_entry(report_docx.render(report, out_dir / f"{name}.docx"), out_dir.parent))
    return files


def _review_text(records, mode, status="draft", signed=None):
    """The review line of the transmittal cover: the review status with the unverified records, and in edit mode that the package is not for production."""
    not_verified = sum(1 for r in records if r["review_status"] != "verified")
    counts = f"{not_verified} of {len(records)} norm records listed in this transmittal are not verified."
    who = f" by {signed['signer']} on {signed['date']}" if signed else ""
    text = {"draft": f"Draft: not approved for construction (D21). {counts}", "for_review": f"In review by the engineer of record. {counts}", "approved": f"Approved{who}. {counts}",
            "approved_for_construction": f"Approved for construction{who}.", "issued": f"Issued{who}. {counts}"}[status]
    return text + (f" {EDIT_MARK}." if mode == "edit" else "")


def findings_text(findings, severity="major"):
    """One line about the open findings of `severity`: how many, and which ids per document (empty text when there is none)."""
    open_ones = [f for f in findings or [] if f.get("severity") == severity and f.get("status", "open") == "open"]
    if not open_ones:
        return ""
    by_doc = {}
    for f in open_ones:
        by_doc.setdefault(f["document"], []).append(f["id"])
    parts = [f"{doc}: {ids[0]}" + (f" to {ids[-1]} ({len(ids)})" if len(ids) > 1 else "") for doc, ids in sorted(by_doc.items())]
    return f"{len(open_ones)} {severity} finding(s) still open. {'; '.join(parts)}. The list is in the manifest."


def accepted_text(findings):
    """One line about the `major` findings the engineer of record accepted: how many, who, and the reason (empty text when none)."""
    done = [f for f in findings or [] if f.get("severity") == "major" and f.get("status") == "accepted"]
    return f"{len(done)} major finding(s) accepted by {done[0]['accepted_by']}: {done[0]['accepted_reason']}" if done else ""


def _cover_header(project, revision, run_id, status, signed, mode):
    header = [["Project", project or ""], ["Revision", revision], ["Run", run_id or ""], ["Status", status.replace("_", " ")]]
    header += [["Signed by", f"{signed['signer']}, {signed['date']}"]] if signed else []
    return header + ([["Mode", EDIT_MARK]] if mode == "edit" else [])


def transmittal_data(transmittal, project, revision, run_id, rows, records, mode="production", status="draft", signed=None, findings=None):
    """The data the transmittal renderer of the drawing engine takes: header, a row per issued file (code, name, file, short hash), the review status (and who signed) with the count of unverified norm records, and the open major findings."""
    table = [[str(n), r.get("code") or "", r["name"], r.get("path") or "(structured document)", r["sha256"][:12]] for n, r in enumerate(rows, start=1)]
    sections = [x for x in (["Review", _review_text(records, mode, status, signed)], ["Open findings", findings_text(findings)], ["Accepted findings", accepted_text(findings)]) if x[1]]
    return {"title": "TRANSMITTAL", "subtitle": transmittal, "header": _cover_header(project, revision, run_id, status, signed, mode),
            "columns": [["No", 0.06], ["Code", 0.2], ["Name", 0.28], ["File", 0.34], ["SHA-256", 0.12]], "rows": table,
            "sections": sections, "footer": f"{project or ''} {transmittal}" + (f" - {EDIT_MARK}" if mode == "edit" else ""), "page_label": PAGE_LABEL}


def render_transmittal(data, work_dir, transmittal):
    """Writes `<work_dir>/documents/<transmittal>_transmittal.pdf` with `epc_drawing.export.transmittal_pdf`; returns (the path relative to `work_dir`, the engine call)."""
    from epc_drawing.export import transmittal_pdf
    out = Path(work_dir) / "documents" / f"{transmittal}_transmittal.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    transmittal_pdf.render(data, out)
    return out.relative_to(work_dir).as_posix(), EC.record_for(ENGINE, "epc_drawing.export.transmittal_pdf.render")


def _reports(docs, project, mode="production", language="en"):
    """([(name, report)] of the documents that have a report structure, [names of the ones that do not])."""
    every = [(name, marked(to_report(name, document, project, language), mode, language)) for name, document in docs.items()]
    return [(n, r) for n, r in every if r is not None], [n for n, r in every if r is None]


def render_all(docs, project, out_dir, formats, mode="production", language="en"):
    """Writes the files of the documents under `out_dir`; returns ({"files": [...], "not_rendered": [...]}, engine calls)."""
    from epc_drawing.export import tables_xlsx
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    reports, skipped = _reports(docs, project, mode, language)
    files = _render_files(reports, out_dir, formats)
    book = out_dir / f"{project or 'documents'}_tables.xlsx"
    if "xlsx" in formats and tables_xlsx.write_tables(book, _sheets(reports)):
        files.append(_entry(book, out_dir.parent))
    return {"files": files, "not_rendered": skipped}, [EC.record_for(ENGINE, FUNCTIONS[f]) for f in ("pdf", "docx") if f in formats]
