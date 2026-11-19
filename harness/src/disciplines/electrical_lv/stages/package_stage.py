"""Stage 12 (package issue): one transmittal `TR-NNN` with ONE manifest that covers every deliverable the earlier stages of this run produced (MIG-32).

The stage is pure: it builds the manifest (`manifest.py`) and the list of files to copy and returns them in `outputs`; the run recorder (which holds the
store's write token) copies the drawing files into `deliverables/TR-NNN/` and writes `.epc/manifests/TR-NNN.manifest.json` through `ProjectStore`.

Transmittal numbers: a run of a revision that has no transmittal yet gets the next number and supersedes the latest open transmittal of another revision; a
run of a revision whose transmittal is still an unsigned draft replaces that draft (same number); a signed or superseded revision blocks (use a new revision).

What counts as a deliverable today:
  - every file sits in a numbered folder of the transmittal by kind: `01_SLD`, `02_MLD`, `03_ARCHITECTURE` (the plans of `inputs/plans/` the building run used), `04_PLANS`, `05_3D`,
    `06_DOCUMENTS` (PDF and Word) and `07_TABLES` (workbook); the cover `TR-NNN_transmittal.pdf` is at the root of the transmittal. A named plan or diagram keeps its own folder inside.
  - drawings: the `.dxf` files of stage 10 (`.svg` is not a deliverable; the `.json` and `.md` files of the engine's output folder are internal);
  - documents: the structured documents of stage 11, whose hash is the one stage 11 recorded (no rendered file exists yet: their `path` is null).

Before the manifests are built the stage runs the cross-document checks of `epc_calc_check` (groups `documents`: memo against stages, hashes, drawing summary,
file bytes) and the findings join the ones the manifest carries; after it is built it checks the manifest itself (schema, labels, hashes against the
recorded ones and the file bytes). Those second findings are reported by the stage and counted in `outputs["calc_check"]`; they cannot be inside the
manifest they describe. The stage never fails because of a finding.

Everything is `draft`: the stage never approves, never signs and never changes a norm review state. With no project store, or with no
deliverable, it returns `not_available` with the reason. `inputs`, `engines`, `findings` and the norm records are those of the whole run up to stage 11.
"""
import copy
import re
from pathlib import Path

from disciplines.electrical_lv import naming
from disciplines.electrical_lv.manifest import DRAFT, ManifestError, build_manifest, sha256_file, supersede
from disciplines.electrical_lv.norm_records import VERIFIED, read_norm_records
from disciplines.electrical_lv.stages import rendering
from disciplines.electrical_lv.stages.base import Stage, StageInputError
from disciplines.electrical_lv.stages.calc_check_stage import by_severity, engine_inputs_for_check, run_dict

DRAWINGS, DOCUMENTS, LAST_PRODUCER = 10, 11, 11
DRAWING_SUFFIXES = (".dxf",)
# Folders of a transmittal, numbered in reading order (UPPER_CASE, as in the naming proposal): the first level of `deliverables/TR-NNN/`.
FOLDER_SLD, FOLDER_MLD, FOLDER_ARCHITECTURE = "01_SLD", "02_MLD", "03_ARCHITECTURE"
FOLDER_PLANS, FOLDER_3D, FOLDER_DOCUMENTS, FOLDER_TABLES, FOLDER_PV = "04_PLANS", "05_3D", "06_DOCUMENTS", "07_TABLES", "08_PV"
TRANSMITTAL = re.compile(r"TR-([0-9]{3,4})")


def run_findings(context):
    """Open findings of stages 1..11 with run-wide ids F-0001, F-0002, ... (the same numbering the run summary and the recorder use)."""
    out, n = [], 0
    for number in sorted(k for k in context.results if k <= LAST_PRODUCER):
        for finding in context.results[number].findings:
            n += 1
            item = copy.deepcopy(finding)
            item["id"] = f"F-{n:04d}"
            if item.get("status", "open") == "open":
                out.append(item)
    return out


def finding_count(context):
    """Number of findings in stages 1..11 (the next finding of the run gets this number + 1)."""
    return sum(len(context.results[k].findings) for k in context.results if k <= LAST_PRODUCER)


def deliverable_bytes(items):
    """{source path: file bytes} of the drawing files that exist (what calc_check compares with the recorded hashes)."""
    return {i["source"]: i["file"].read_bytes() for i in items if i["file"] is not None and i["file"].is_file()}


def run_engine_calls(context):
    return [dict(c) for k in sorted(context.results) if k <= LAST_PRODUCER for c in context.results[k].engine_calls]


def _ok(context, number):
    res = context.results.get(number)
    return res if res is not None and res.status == "ok" else None


def drawing_folder(stem):
    """Transmittal folder of a drawing, from the file name stage 10 and stage 9b give it: single-line diagrams, board layouts, 3D views and sections, and plans."""
    for prefix, folder in (("SLD", FOLDER_SLD), ("MLD", FOLDER_MLD)):
        if stem.startswith(prefix + "_"):
            return folder
    if any(mark in stem for mark in ("_model_3d", "_section_", "_elevation_")):
        return FOLDER_3D
    if "_pv_" in stem:
        return FOLDER_PV
    return FOLDER_PLANS


def document_folder(suffix):
    """Transmittal folder of a rendered document: the workbook of the tables apart from the reports (PDF and Word)."""
    return FOLDER_TABLES if suffix == ".xlsx" else FOLDER_DOCUMENTS


def in_folder(item, folder):
    """Put a deliverable that has a file under `folder` (the path inside the transmittal becomes `<folder>/<path>`)."""
    if item["path"]:
        item["path"] = f"{folder}/{item['path']}"
    item["folder"] = folder
    return item


def _building_floors(context):
    """The floors of `engine_inputs.building` that name a plan file."""
    building = (getattr(context, "engine_inputs", None) or {}).get("building") or {}
    return [f for f in building.get("floors") or [] if isinstance(f, dict) and f.get("plan")]


def _plan_files(context):
    """[(plan name as given, floor, file)] of the floors whose plan file exists in `inputs/plans/` (each plan once)."""
    store = getattr(context, "store", None)
    found = {}
    for floor in _building_floors(context) if store is not None else []:
        file = Path(store.inputs_dir) / floor["plan"]
        if file.is_file():
            found.setdefault(floor["plan"], (floor, file))
    return [(plan, floor, file) for plan, (floor, file) in found.items()]


def _sheet_files(context):
    """The other sheets of the architecture (`engine_inputs.building.presentation_sheets`, files of `inputs/`) that exist, each once."""
    store = getattr(context, "store", None)
    building = (getattr(context, "engine_inputs", None) or {}).get("building") or {}
    given = [s for s in building.get("presentation_sheets") or [] if isinstance(s, str)]
    return [(s, Path(store.inputs_dir) / s) for s in dict.fromkeys(given) if store is not None and (Path(store.inputs_dir) / s).is_file()]


def _architecture(context):
    """The architecture plans the building run used (`engine_inputs.building.floors[].plan`, files of `inputs/plans/`): the DXF as the engineer gave it, copied to `03_ARCHITECTURE/`.
    A supporting file, not a document of the issue: it needs no entry in `deliverable_names`."""
    return [{"name": f"architecture_{Path(plan).stem}", "title": f"Architecture plan {floor.get('name') or floor.get('id')}", "path": f"{FOLDER_ARCHITECTURE}/{Path(plan).name}",
             "code": None, "file": file, "recorded": sha256_file(file), "source": str(file), "support": True, "folder": FOLDER_ARCHITECTURE}
            for plan, floor, file in _plan_files(context)] + [
        {"name": f"architecture_{Path(s).stem}", "title": f"Architecture sheet {Path(s).stem}", "path": f"{FOLDER_ARCHITECTURE}/{Path(s).name}", "code": None, "file": file,
         "recorded": sha256_file(file), "source": str(file), "support": True, "folder": FOLDER_ARCHITECTURE} for s, file in _sheet_files(context)]


def _drawings(context):
    res = _ok(context, DRAWINGS)
    if res is None:
        return []
    out = []
    for f in res.outputs.get("files", []):
        if not f["path"].endswith(DRAWING_SUFFIXES):
            continue
        file = Path(context.work_dir or "") / res.outputs["directory"] / f["path"]
        out.append(in_folder({"name": Path(f["path"]).stem, "title": f"Drawing {f['path']}", "path": f["path"], "code": None, "file": file, "recorded": f["sha256"],
                              "source": f"{res.outputs['directory']}/{f['path']}"}, drawing_folder(Path(f["path"]).stem)))
    return out


def _documents(context):
    res = _ok(context, DOCUMENTS)
    docs = res.outputs.get("documents", []) if res is not None else []
    return [{"name": d["name"], "title": d["name"].replace("_", " ").capitalize(), "path": None, "code": None, "file": None, "recorded": d["sha256"], "source": None}
            for d in docs]


def _rendered(context):
    """The files of the documents that stage 11 rendered (PDF, Word, workbook): named `<document>_<format>`, copied from `<work_dir>/documents/`."""
    res = _ok(context, DOCUMENTS)
    files = ((res.outputs.get("rendered") or {}).get("files") or []) if res is not None else []
    return [in_folder({"name": f["name"], "title": f"Document file {f['path']}", "path": Path(f["path"]).name, "code": None, "file": Path(context.work_dir or "") / f["path"],
                       "recorded": f["sha256"], "source": f["path"]}, document_folder(Path(f["path"]).suffix)) for f in files]


def _unrendered(documents, rendered):
    stems = {r["name"].rsplit("_", 1)[0] for r in rendered}
    return [d for d in documents if d["name"] not in stems]


def deliverables(context):
    """Drawings, rendered files and the structured documents that have no rendered file (one that has them is listed through its files, not twice: B-06)."""
    rendered = _rendered(context)
    return _drawings(context) + _architecture(context) + rendered + _unrendered(_documents(context), rendered)


def _name_one(item, names, project_code, code_ok):
    """Name one deliverable from its entry in `names`; the errors of its entry (empty when named, or when the project code is not usable)."""
    if item.get("support"):
        return []
    entry = names.get(item["name"])
    bad = ["no entry in engine_inputs.deliverable_names"] if entry is None else naming.problems(entry)
    if not bad and code_ok:
        item["code"] = naming.document_code(project_code, entry)
        if item["file"] is not None:
            item["path"] = f"{item['folder']}/{naming.file_path(project_code, entry, Path(item['path']).suffix)}"
    return [f"{item['name']}: {b}" for b in bad]


def _shared_paths(items):
    paths = [i["path"] for i in items if i["path"]]
    return [f"two files share the path {p}" for p in sorted({p for p in paths if paths.count(p) > 1})]


def apply_names(items, names, project_code):
    """Give every deliverable its document code and, for a drawing file, its path inside the transmittal, from `engine_inputs.deliverable_names`.

    `names` is {engine name: naming entry} (see `naming.py`). A deliverable without an entry, an invalid entry, a project code that is not
    AAAA-PROVIDER-CLIENT-CODE or two files with one path stop the stage: no name is invented.
    """
    code_ok = bool(naming.PROJECT_CODE.fullmatch(project_code or ""))
    errors = [] if code_ok else [f"the project code {project_code!r} must be AAAA-PROVIDER-CLIENT-CODE to name deliverables"]
    names = names if isinstance(names, dict) else {}
    for item in items:
        if not item.get("support"):
            errors += _name_one(item, names, project_code, code_ok)
    errors += _shared_paths(items)
    if errors:
        raise StageInputError(errors)


def _file_hash(item):
    """The SHA-256 of a deliverable; a drawing file must still match the hash stage 10 recorded."""
    if item["file"] is None:
        return item["recorded"]
    if not item["file"].is_file():
        raise StageInputError([f"{item['source']}: the drawing file recorded by stage 10 is missing"])
    sha = sha256_file(item["file"])
    if sha != item["recorded"]:
        raise StageInputError([f"{item['source']}: the file changed after stage 10 (hash differs from the recorded one)"])
    return sha


def _number(manifest):
    return int(TRANSMITTAL.fullmatch(manifest["transmittal"]).group(1))


def _refuse_closed(manifest, revision):
    """A signed or already superseded transmittal of `revision` cannot be regenerated."""
    if manifest["signed"] is not None:
        raise StageInputError([f"{manifest['transmittal']} (revision {revision}) is signed: use a new revision to regenerate it"])
    if manifest["superseded_by"] is not None:
        raise StageInputError([f"{manifest['transmittal']} (revision {revision}) is already superseded by {manifest['superseded_by']}: use a new revision"])


def _refuse_edit_to_production(manifest, revision, mode):
    """A production run does not take over a revision that was made in edit mode (ADR-0035): that package is not for production, a new revision is."""
    if manifest.get("mode") == "edit" and mode != "edit":
        raise StageInputError([f"revision {revision} ({manifest['transmittal']}) was made in edit mode: it is not for production, use a new revision"])


def plan_transmittal(store, revision, mode="production"):
    """(transmittal id, previous, same): the id this run writes, the open manifest of another revision it supersedes (or None) and the unsigned draft of the
    same revision it replaces (or None). A signed or already superseded transmittal of this revision blocks."""
    existing = [m for _, m in store.read_manifests()]
    same = sorted((m for m in existing if m["revision"] == revision), key=_number)
    for m in same:
        _refuse_closed(m, revision)
        _refuse_edit_to_production(m, revision, mode)
    if same:
        return same[-1]["transmittal"], None, same[-1]
    open_ones = sorted((m for m in existing if m["superseded_by"] is None), key=_number)
    nxt = max((_number(m) for m in existing), default=0) + 1
    return f"TR-{nxt:03d}", (open_ones[-1] if open_ones else None), None


class PackageIssueStage(Stage):
    """Stage 12: the manifest (`draft`) and the transmittal folder of the deliverables of this run."""

    wired = True
    wiring_task = "MIG-32"

    def _unavailable(self, reason, message):
        return self.result("not_available", message=message, reason=reason)

    def _manifest(self, context, transmittal, files, records, extra=()):
        project = (context.profile or {}).get("project_code") or ""
        try:
            return build_manifest(transmittal=transmittal, title=f"{project} {transmittal} revision {context.revision}".strip(), revision=context.revision,
                                  run_id=context.pipeline_run_id, inputs_manifest=self._inputs(context), engine_calls=run_engine_calls(context),
                                  normative_profile=(context.profile or {}).get("normative_profile"), files=files,
                                  findings=run_findings(context) + list(extra), review_status=DRAFT, norm_reader=lambda _p: records, mode=getattr(context, "mode", "production"))
        except ManifestError as exc:
            raise StageInputError(exc.errors) from exc

    @staticmethod
    def _inputs(context):
        store = context.store
        return store.read_ssot("inputs_manifest.json") if store.is_frozen() else context.inputs_manifest

    def _nothing_to_issue(self, store):
        if store is None:
            return self._unavailable("no_store", "no project store: the manifest is written under .epc/manifests/ of a project folder")
        return self._unavailable("no_deliverables", "no deliverable to issue: stages 10 and 11 produced no drawing file or document in this run")

    @staticmethod
    def _given_or_catalogue(context, items):
        """`engine_inputs.deliverable_names`, or (project code AAAA-PROV-CLI-CODE) the names of the catalogue for the items (SIM-10); None when neither applies."""
        given = (context.engine_inputs or {}).get("deliverable_names")
        if given is not None or not naming.PROJECT_CODE.fullmatch((context.profile or {}).get("project_code") or ""):
            return given
        return naming.automatic([i["name"] for i in items if not i.get("support")], _floors(context))

    @classmethod
    def _name_items(cls, context, items):
        """Names the deliverables from the given or the catalogue names; returns them (None when there are none)."""
        names = cls._given_or_catalogue(context, items)
        if names is not None:
            apply_names(items, names, (context.profile or {}).get("project_code"))
        return names

    def _manifest_of(self, context, plan, rows, records, before):
        """(manifest, superseded entries) of the transmittal: it supersedes the open one of another revision or takes over the draft of this revision."""
        transmittal, previous, same = plan
        manifest = self._manifest(context, transmittal, [{k: r[k] for k in ("name", "title", "code", "path", "sha256")} for r in rows], records, before)
        replaced = []
        if previous:
            old, manifest = supersede(previous, manifest)
            replaced.append({"path": context.store.manifest_rel(old), "manifest": old})
        elif same:
            manifest["supersedes"] = same["supersedes"]
        return manifest, replaced

    @staticmethod
    def _outputs(context, where, produced, rows, records):
        """The result of the stage: the manifest, what it supersedes, the files to copy, the norm records count and the transmittal list."""
        (transmittal, path), (manifest, replaced, copies) = where, produced
        return {"revision": context.revision, "manifests": [{"path": path, "manifest": manifest}], "superseded": replaced, "copies": copies,
                "norm_records": {"listed": len(records), "not_verified": sum(1 for r in records if r["review_status"] != VERIFIED)},
                "transmittal": {"id": transmittal, "project_code": (context.profile or {}).get("project_code"), "revision": context.revision,
                                "pipeline_run_id": context.pipeline_run_id, "review_status": DRAFT, "manifest": path, "files": rows}}

    @staticmethod
    def _message(context, transmittal, rows, records, longest):
        not_verified = sum(1 for r in records if r["review_status"] != VERIFIED)
        msg = f"transmittal {transmittal} (revision {context.revision}): {len(rows)} file(s), draft; {not_verified} of {len(records)} norm records not verified"
        if getattr(context, "mode", "production") == "edit":
            msg += "; EDIT MODE (not for production)"
        if longest > naming.PATH_WARNING:
            msg += f"; WARNING: a file path has {longest} characters (Windows stops at about 260): shorten the project folder or the descriptions"
        return msg

    def execute(self, context):
        store = context.store
        items = deliverables(context) if store is not None else []
        if not items:
            return self._nothing_to_issue(store)
        records = read_norm_records(sorted({c["function"].split(".")[0] for c in run_engine_calls(context)}))
        import epc_calc_check
        files, project, start = deliverable_bytes(items), engine_inputs_for_check(context), finding_count(context) + 1
        before = epc_calc_check.check_run(run_dict(context, LAST_PRODUCER), project=project, files=files, run_id=context.pipeline_run_id, start_id=start,
                                          groups=("documents",))
        names = self._name_items(context, items)
        plan = plan_transmittal(store, context.revision, getattr(context, "mode", "production"))
        transmittal = plan[0]
        rows = [{"name": i["name"], "title": i["title"], "code": i["code"], "path": i["path"], "sha256": _file_hash(i), "source": i["source"]} for i in items]
        manifest, replaced = self._manifest_of(context, plan, rows, records, before)
        path = store.manifest_rel(manifest)
        copies = [{"source": i["source"], "to": f"deliverables/{transmittal}/{i['path']}"} for i in items if i["file"] is not None]
        calls = self._cover(context, transmittal, rows, records, copies, manifest["findings"])
        outputs = self._outputs(context, (transmittal, path), (manifest, replaced, copies), rows, records)
        after = self._check_manifests(context, outputs, files, project, start + len(before))
        outputs["calc_check"] = {"findings_count": len(before) + len(after), "by_severity": by_severity(before + after)}
        longest = max((len(f"{store.root}/deliverables/{transmittal}/{r['path']}") for r in rows if r["path"]), default=0)
        outputs["naming"] = {"named": names is not None, "longest_path": longest}
        notes = self._edit_note(context, len(before) + len(after) + start, records)
        return self.result("ok", outputs=self._with_mode(outputs, context), findings=before + after + notes, engine_calls=calls,
                           message=self._message(context, transmittal, rows, records, longest))

    @staticmethod
    def _with_mode(outputs, context):
        """The outputs of the stage; those of an edit-mode package say so (a production one has no `mode`, as it never had)."""
        return dict(outputs, mode="edit") if getattr(context, "mode", "production") == "edit" else outputs

    @staticmethod
    def _edit_note(context, number, records):
        """In edit mode, one note that says what the mode let through: the norm records that are not verified (information, never an error)."""
        if getattr(context, "mode", "production") != "edit":
            return []
        bad = sum(1 for r in records if r["review_status"] != VERIFIED)
        return [{"id": f"F-{number:04d}", "run_id": context.pipeline_run_id, "verifier": "final-auditor", "severity": "note", "document": "manifest", "field": "mode",
                 "value": f"edit mode: {bad} of {len(records)} norm records are not verified", "expected": "production mode with every record verified before construction",
                 "clause": "ADR-0035", "action": "This package is for checking the system, not for production: rerun in production mode once the records are verified.", "evidence": ["manifest mode edit"], "status": "open"}]

    @staticmethod
    def _cover(context, transmittal, rows, records, copies, findings=()):
        """The cover PDF of the transmittal (when the run renders PDF files, see `rendering.py`): written under the work folder and copied with the other files; it lists them, so it is not one of them
        in the manifest. Returns the engine calls."""
        if "pdf" not in rendering.formats_of(context) or not context.work_dir:
            return []
        data = rendering.transmittal_data(transmittal, (context.profile or {}).get("project_code"), context.revision, context.pipeline_run_id, rows, records, getattr(context, "mode", "production"),
                                         findings=findings)
        source, call = rendering.render_transmittal(data, context.work_dir, transmittal)
        copies.append({"source": source, "to": f"deliverables/{transmittal}/{transmittal}_transmittal.pdf"})
        return [call]

    @staticmethod
    def _check_manifests(context, outputs, files, project, start):
        """calc_check on the manifest just built (it cannot carry the findings about itself)."""
        import epc_calc_check
        run = run_dict(context, LAST_PRODUCER)
        run["results"].append({"stage": 16, "status": "ok", "outputs": outputs, "findings": []})
        return epc_calc_check.check_run(run, project=project, files=files, run_id=context.pipeline_run_id, start_id=start, groups=("manifests",))
