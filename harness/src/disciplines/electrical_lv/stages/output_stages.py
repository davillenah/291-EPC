"""Stage 10 (drawings) and stage 11 (documents): they call the engines that draw and write; the discipline draws and writes nothing.

Drawings are written by `epc_drawing.board_design.design` only under `context.work_dir`. The documents are the structured
documents `epc_aea90364.board_memo` produces from the same calculation (single source), plus the terminal-block list of `epc_terminal_blocks` (MIG-39b, no file) and, only when the engineer gives `engine_inputs["boq"]["allowance_pct"]`, the draft bill of quantities of `epc_boq` (MIG-39c, no file) and, only when `engine_inputs["datasheets"]["catalog_dir"]` names a catalog folder, the draft datasheets of `epc_datasheets` (MIG-39d, no file) and, only when the BOQ was produced and `engine_inputs["rfq"]` carries the commercial terms, the draft request for quotation of `epc_rfq` (MIG-39e, no file, no prices) and, whenever the context has the profile and the design basis of stage 2, the draft design-basis document of `epc_design_basis` (MIG-39f, no file; the limits are read by the engine from the calculation engines) and, right after it (it consumes it), the draft descriptive report of `epc_descriptive_report` (MIG-39g, no file); the ones whose engine does not exist
yet are listed by name as planned, never with a value.
"""
import copy
import datetime
import hashlib
import json
import re
from pathlib import Path

from disciplines.electrical_lv.norm_records import VERIFIED, read_norm_records
from disciplines.electrical_lv.stages import engine_calls as EC
from disciplines.electrical_lv.stages.base import Stage, StageInputError
from disciplines.electrical_lv.stages.cable_list import cable_list_document
from disciplines.electrical_lv.stages.mappings import ENGINE_CHAIN, PENDING_DOCUMENTS

DESIGN = "epc_drawing.board_design.design"
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
DATE_FORMAT = re.compile(r"\d{4}-\d{2}-\d{2}")
SUMMARY_KEYS = ("name", "ok", "circuits", "groups", "non_compliant", "diagrams", "log")


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def list_files(root):
    """Every file under `root` as {path (posix, relative), bytes, sha256}, sorted by path."""
    root = Path(root)
    return [{"path": p.relative_to(root).as_posix(), "bytes": p.stat().st_size, "sha256": sha256_of(p)} for p in sorted(root.rglob("*")) if p.is_file()]


def drawing_date(context):
    """The date the engineer pinned for the drawings, `engine_inputs["drawings"]["date"]` (YYYY-MM-DD), as an ISO string; None when none was given.

    With a date the drawing engine writes it (title block, DXF times, GUIDs derived from it, workbook properties) instead of the clock and random GUIDs, so the same inputs give
    byte-identical files. Without it nothing is pinned (today's date, as always). An invalid date blocks the stage."""
    given = EC.inputs_of(context).get("drawings")
    value = given.get("date") if isinstance(given, dict) else None
    if value is None:
        return None
    if not (isinstance(value, str) and DATE_FORMAT.fullmatch(value)):
        raise StageInputError([f"engine_inputs.drawings.date: {value!r} is not an ISO date (YYYY-MM-DD)"])
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        raise StageInputError([f"engine_inputs.drawings.date: {value!r} is not a calendar date"]) from None
    return value


class DrawingsStage(Stage):
    """Stage 10: the single-line diagram of the board, drawn by the drawing engine into `<work_dir>/drawings/<board name>/out`."""

    wired = True
    wiring_task = "MIG-30c"
    diagrams = ("sld",)

    def _target(self, context, name):
        if not context.work_dir:
            raise StageInputError(["work_dir: no work_dir was given, so the drawings have nowhere to be written"])
        if not SAFE_NAME.fullmatch(str(name)):
            raise StageInputError([f"board name {name!r} cannot be used as a drawing file name (letters, digits, - and _ only)"])
        return Path(context.work_dir) / "drawings" / name

    def execute(self, context):
        from epc_drawing import board_design
        ch = EC.chain(context)
        name = ch["form"]["board"]["name"]
        target = self._target(context, name)
        summary = board_design.design(copy.deepcopy(ch["form"]), target, name, ch["criteria"], None, diagrams=self.diagrams, drawing_date=drawing_date(context))
        calls = [EC.record_for("cad/drawing", DESIGN)]
        if not summary["ok"]:
            return self.result("failed", message=f"drawing engine: {summary['error']}", reason="engine", engine_calls=calls)
        outputs = {"directory": f"drawings/{name}/out", "files": list_files(target / "out"), "summary": {k: copy.deepcopy(summary[k]) for k in SUMMARY_KEYS}}
        return self.result("ok", outputs=outputs, engine_calls=calls)


TERMINAL_LIST = "epc_terminal_blocks.build_terminal_list"
TERMINAL_ENGINE = "quality/terminal_blocks"


def terminal_circuits(ch):
    """The terminal-list input of each circuit, selected from the engine result of stages 6 and 8 (no arithmetic)."""
    rows = []
    for tag, data in ch["calc"]["datos"].items():
        detail = ch["calc"]["detalle"][tag]
        rows.append({"tag": tag, "phases": detail["fases"], "s_mm2": data["S"], "pe_mm2": detail.get("pe_mm2"), "neutral_mm2": detail.get("neutro_mm2"),
                     "description": detail.get("descripcion") or "", "device": data.get("disp") or "", "in_a": data.get("In")})
    return rows


CABLE_LIST_PENDING_NAME = "cable list"

BOQ_BUILD = "epc_boq.build_boq"
BOQ_ENGINE = "procurement/boq"
BOQ_PENDING_NAME = "BOQ"
NO_ALLOWANCE = "no_allowance_pct"


def boq_circuits(ch):
    """The bill-of-quantities input of each circuit, selected from the engine result of stages 6 and 8 (no arithmetic). The first element of the device chain is the protective device."""
    rows = []
    for tag, data in ch["calc"]["datos"].items():
        detail = ch["calc"]["detalle"][tag]
        head = (detail.get("cadena") or [{}])[0]
        rows.append({"tag": tag, "phases": detail["fases"], "s_mm2": data["S"], "neutral_mm2": detail.get("neutro_mm2"), "pe_mm2": detail.get("pe_mm2"),
                     "length_m": detail.get("largo_m"), "material": detail.get("material"), "insulation": detail.get("aislacion"),
                     "device_kind": head.get("short"), "in_a": data.get("In"), "poles": head.get("poles"), "breaking_capacity_ka": data.get("icu")})
    return rows


def boq_allowance(context):
    """The wastage percentage the engineer gave, or None: it is never defaulted."""
    given = EC.inputs_of(context).get("boq")
    return given.get("allowance_pct") if isinstance(given, dict) else None


DATASHEETS_BUILD = "epc_datasheets.build_datasheets"
DATASHEETS_ENGINE = "procurement/datasheets"
DATASHEETS_PENDING_NAME = "datasheets"
NO_CATALOG_DIR = "no_catalog_dir"


def datasheets_inputs(context):
    """The explicit datasheets input `{"catalog_dir", "voltage_v"?}` the engineer gave, or None: the stage never searches the repository for a catalog."""
    given = EC.inputs_of(context).get("datasheets")
    return given if isinstance(given, dict) and given.get("catalog_dir") else None


RFQ_BUILD = "epc_rfq.build_rfq"
RFQ_ENGINE = "procurement/rfq"
RFQ_PENDING_NAME = "RFQ"
NO_BOQ = "no_boq"
NO_RFQ_TERMS = "no_rfq_terms"
RFQ_OPTIONAL = ("payment_terms", "notes", "requestable_categories")
RFQ_KEYS = ("suppliers", "currency", "response_deadline", "delivery_site", "validity_days") + RFQ_OPTIONAL


def rfq_inputs(context):
    """The explicit commercial terms `engine_inputs["rfq"]` the engineer gave, or None when nothing was given. A non-empty object is passed to the engine as it is: it
    names every missing required field (the stage is then blocked); the stage never defaults a commercial value."""
    given = EC.inputs_of(context).get("rfq")
    return given if isinstance(given, dict) and given else None


DESIGN_BASIS_BUILD = "epc_design_basis.build_design_basis_document"
DESIGN_BASIS_ENGINE = "quality/design_basis"
DESIGN_BASIS_PENDING_NAME = "design basis"
NO_DESIGN_BASIS = "no_design_basis"


DESCRIPTIVE_BUILD = "epc_descriptive_report.build_descriptive_report"
DESCRIPTIVE_ENGINE = "quality/descriptive_report"
DESCRIPTIVE_PENDING_NAME = "descriptive report"


def report_circuits(ch):
    """The descriptive-report input of each circuit: the bill-of-quantities fields plus the load kind and the description, selected from the engine result (no arithmetic)."""
    return [dict(row, kind=ch["kinds"].get(row["tag"]), description=ch["calc"]["detalle"][row["tag"]].get("descripcion")) for row in boq_circuits(ch)]


def unreviewed_norm_records(context, calls):
    """Number of norm records not verified among those of the engines called so far in this run (the count the manifest of stage 12 lists; read only)."""
    previous = [c for number in sorted(context.results) for c in context.results[number].engine_calls]
    records = read_norm_records(sorted({c["function"].split(".")[0] for c in previous + calls}))
    return sum(1 for r in records if r["review_status"] != VERIFIED)


def document_entry(name, document):
    """A document of the outputs: its name, the SHA-256 of its canonical JSON (the convention of the memo documents) and the structure (no file)."""
    return {"name": name, "sha256": hashlib.sha256(json.dumps(document, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest(), "document": document}


class DocumentsStage(Stage):
    """Stage 11: calculation memo and project summary from the engine, the terminal-block list (MIG-39b); the other documents are reported as planned."""

    wired = True
    wiring_task = "MIG-30c"
    calls = ("epc_aea90364.board_memo.memoria_doc", "epc_aea90364.board_memo.sintesis_doc")

    @staticmethod
    def boq(ch, allowance, terminal_totals):
        import epc_boq
        try:
            return epc_boq.build_boq(ch["form"]["board"]["name"], boq_circuits(ch), allowance_pct=allowance, terminal_totals=terminal_totals)
        except ValueError as exc:
            raise StageInputError([f"bill of quantities: {exc}"]) from exc

    @staticmethod
    def datasheets(ch, given):
        """The datasheet records: the catalog is read through `epc_datasheets.load_catalog_dir` from the folder the engineer gave (nothing else is read)."""
        import epc_datasheets
        try:
            catalog = epc_datasheets.load_catalog_dir(given["catalog_dir"])
            requirements = epc_datasheets.requirements_from_circuits(boq_circuits(ch), given.get("voltage_v"))
            return epc_datasheets.build_datasheets(ch["form"]["board"]["name"], requirements, catalog)
        except ValueError as exc:
            raise StageInputError([f"datasheets: {exc}"]) from exc

    @staticmethod
    def rfq(ch, given, docs):
        """The draft request for quotation from the bill of quantities (and the datasheets when produced) and the engineer's terms."""
        import epc_rfq
        unknown = sorted(set(given) - set(RFQ_KEYS))
        try:
            if unknown:
                raise ValueError(f"unknown input(s) {', '.join(unknown)}")
            return epc_rfq.build_rfq(ch["form"]["board"]["name"], docs["boq"], datasheets=docs.get("datasheets"), **given)
        except ValueError as exc:
            raise StageInputError([f"rfq: {exc}"]) from exc

    def rfq_document(self, context, ch, docs, calls, pending):
        """Adds the request for quotation only when the BOQ was produced in this run AND the terms were given; otherwise `RFQ` stays pending with a reason."""
        given = rfq_inputs(context)
        reason = NO_BOQ if "boq" not in docs else NO_RFQ_TERMS if given is None else None
        if reason:
            return [dict(p, reason=reason) if p["name"] == RFQ_PENDING_NAME else p for p in pending]
        docs["rfq"] = self.rfq(ch, given, docs)
        calls.append(EC.record_for(RFQ_ENGINE, RFQ_BUILD))
        return [p for p in pending if p["name"] != RFQ_PENDING_NAME]

    def optional_documents(self, context, ch, terminals, docs, calls, pending):
        """Adds the bill of quantities, the datasheets and the request for quotation when their explicit inputs are given; returns the pending list (a reason where an input is missing)."""
        allowance = boq_allowance(context)
        if allowance is None:
            pending = [dict(p, reason=NO_ALLOWANCE) if p["name"] == BOQ_PENDING_NAME else p for p in pending]
        else:
            docs["boq"] = self.boq(ch, allowance, terminals["totals"])
            pending = [p for p in pending if p["name"] != BOQ_PENDING_NAME]
            calls.append(EC.record_for(BOQ_ENGINE, BOQ_BUILD))
        given = datasheets_inputs(context)
        if given is None:
            pending = [dict(p, reason=NO_CATALOG_DIR) if p["name"] == DATASHEETS_PENDING_NAME else p for p in pending]
        else:
            docs["datasheets"] = self.datasheets(ch, given)
            calls.append(EC.record_for(DATASHEETS_ENGINE, DATASHEETS_BUILD))
            pending = [p for p in pending if p["name"] != DATASHEETS_PENDING_NAME]
        return self.rfq_document(context, ch, docs, calls, pending)

    @staticmethod
    def design_basis(context):
        """The design-basis document from the same inputs as stage 2 (profile, criteria, assumptions, requirements); the limits are read by the engine from the calculation engines."""
        import epc_design_basis
        try:
            return epc_design_basis.build_design_basis_document(context.profile, criteria=context.criteria, assumptions=context.assumptions, requirements=context.requirements)
        except ValueError as exc:
            raise StageInputError([f"design basis: {exc}"]) from exc

    def design_basis_document(self, context, docs, calls, pending):
        """Adds the design basis when the context has a profile and the design basis of stage 2; otherwise it is listed as pending with a reason."""
        if context.profile is None or context.design_basis is None:
            return pending + [{"name": DESIGN_BASIS_PENDING_NAME, "status": "planned", "reason": NO_DESIGN_BASIS}]
        docs["design_basis"] = self.design_basis(context)
        calls.append(EC.record_for(DESIGN_BASIS_ENGINE, DESIGN_BASIS_BUILD))
        return pending

    @staticmethod
    def descriptive_report(context, ch, terminals, docs, calls, pending):
        """The descriptive report from the design basis and the circuit summary, with the terminal totals, the BOQ and the state of the run so far."""
        import epc_descriptive_report
        try:
            return epc_descriptive_report.build_descriptive_report(
                docs["design_basis"], report_circuits(ch), terminals=terminals, boq=docs.get("boq"),
                pending_documents=[p for p in pending if p["name"] != DESCRIPTIVE_PENDING_NAME], unreviewed_norm_records=unreviewed_norm_records(context, calls))
        except ValueError as exc:
            raise StageInputError([f"descriptive report: {exc}"]) from exc

    def descriptive_report_document(self, context, ch, terminals, docs, calls, pending):
        """Adds the descriptive report after the design basis (it consumes it); without the design basis it stays pending with a reason."""
        if "design_basis" not in docs:
            return [dict(p, reason=NO_DESIGN_BASIS) if p["name"] == DESCRIPTIVE_PENDING_NAME else p for p in pending]
        docs["descriptive_report"] = self.descriptive_report(context, ch, terminals, docs, calls, pending)
        calls.append(EC.record_for(DESCRIPTIVE_ENGINE, DESCRIPTIVE_BUILD))
        return [p for p in pending if p["name"] != DESCRIPTIVE_PENDING_NAME]

    @staticmethod
    def lighting_study(context):
        """The lighting study of stage 3 as a document (the engine result as it is, draft); None when stage 3 did not run the lighting slice."""
        res = context.results.get(3)
        result = (res.outputs.get("lighting") if res is not None and res.status == "ok" else None)
        if result is None:
            return None
        return {"document": "lighting_study", "status": "draft", "engine": copy.deepcopy(result["engine"]), "result": copy.deepcopy(result)}

    @staticmethod
    def routing(context):
        """The routing section of stage 3 when it ran the slice, else None."""
        res = context.results.get(3)
        return res.outputs.get("routing") if res is not None and res.status == "ok" else None

    def cable_list(self, context, ch, docs, pending):
        """The cable list, only when stage 3 routed the floors (a run without routing keeps `cable list` pending: the list is made of the circuits and of the runs that carry them)."""
        routing = self.routing(context)
        if routing is None:
            return pending
        docs["cable_list"] = cable_list_document(ch, (context.loads or {}).get("loads") or [], routing)
        return [p for p in pending if p["name"] != CABLE_LIST_PENDING_NAME]

    def execute(self, context):
        import epc_terminal_blocks
        from epc_aea90364 import board_memo
        ch = EC.chain(context)
        memo = ch["memo"]
        try:
            terminals = epc_terminal_blocks.build_terminal_list(ch["form"]["board"]["name"], terminal_circuits(ch))
        except ValueError as exc:
            raise StageInputError([f"terminal-block list: {exc}"]) from exc
        docs = {"calculation_memo": board_memo.memoria_doc(memo), "project_summary": board_memo.sintesis_doc(memo), "terminal_block_list": terminals}
        calls = [EC.record_for(ENGINE_CHAIN, fn) for fn in self.calls] + [EC.record_for(TERMINAL_ENGINE, TERMINAL_LIST)]
        study = self.lighting_study(context)
        if study is not None:
            docs["lighting_study"] = study
        pending = [{"name": n, "status": "planned"} for n in PENDING_DOCUMENTS]
        pending = self.optional_documents(context, ch, terminals, docs, calls, pending)
        pending = self.cable_list(context, ch, docs, pending)
        pending = self.design_basis_document(context, docs, calls, pending)
        pending = self.descriptive_report_document(context, ch, terminals, docs, calls, pending)
        outputs = {"documents": [document_entry(n, d) for n, d in docs.items()], "memo_summary": copy.deepcopy(memo["resumen"]), "pending_documents": pending}
        return self.result("ok", outputs=outputs, engine_calls=calls)
