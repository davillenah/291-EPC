"""Stage 16 (package issue): one transmittal `TR-NNN` with ONE manifest that covers every deliverable the earlier stages of this run produced (MIG-32).

The stage is pure: it builds the manifest (`manifest.py`) and the list of files to copy and returns them in `outputs`; the run recorder (which holds the
store's write token) copies the drawing files into `deliverables/TR-NNN/` and writes `.epc/manifests/TR-NNN.manifest.json` through `ProjectStore`.

Transmittal numbers: a run of a revision that has no transmittal yet gets the next number and supersedes the latest open transmittal of another revision; a
run of a revision whose transmittal is still an unsigned draft replaces that draft (same number); a signed or superseded revision blocks (use a new revision).

What counts as a deliverable today:
  - drawings: the `.dxf` files of stage 14 (`.svg` is not a deliverable; the `.json` and `.md` files of the engine's output folder are internal);
  - documents: the structured documents of stage 15, whose hash is the one stage 15 recorded (no rendered file exists yet: their `path` is null).

Before the manifests are built the stage runs the cross-document checks of `epc_calc_check` (groups `documents`: memo against stages, hashes, drawing summary,
file bytes) and the findings join the ones the manifest carries; after it is built it checks the manifest itself (schema, labels, hashes against the
recorded ones and the file bytes). Those second findings are reported by the stage and counted in `outputs["calc_check"]`; they cannot be inside the
manifest they describe. The stage never fails because of a finding.

Everything is `draft`: the stage never approves, never signs and never changes a norm review state. With no project store, or with no
deliverable, it returns `not_available` with the reason. `inputs`, `engines`, `findings` and the norm records are those of the whole run up to stage 15.
"""
import copy
import re
from pathlib import Path

from disciplines.electrical_lv import naming
from disciplines.electrical_lv.manifest import DRAFT, ManifestError, build_manifest, sha256_file, supersede
from disciplines.electrical_lv.norm_records import VERIFIED, read_norm_records
from disciplines.electrical_lv.stages.base import Stage, StageInputError
from disciplines.electrical_lv.stages.calc_check_stage import by_severity, engine_inputs_for_check, run_dict

DRAWINGS, DOCUMENTS, LAST_PRODUCER = 14, 15, 15
DRAWING_SUFFIXES = (".dxf",)
TRANSMITTAL = re.compile(r"TR-([0-9]{3,4})")


def run_findings(context):
    """Open findings of stages 1..15 with run-wide ids F-0001, F-0002, ... (the same numbering the run summary and the recorder use)."""
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
    """Number of findings in stages 1..15 (the next finding of the run gets this number + 1)."""
    return sum(len(context.results[k].findings) for k in context.results if k <= LAST_PRODUCER)


def deliverable_bytes(items):
    """{source path: file bytes} of the drawing files that exist (what calc_check compares with the recorded hashes)."""
    return {i["source"]: i["file"].read_bytes() for i in items if i["file"] is not None and i["file"].is_file()}


def run_engine_calls(context):
    return [dict(c) for k in sorted(context.results) if k <= LAST_PRODUCER for c in context.results[k].engine_calls]


def _ok(context, number):
    res = context.results.get(number)
    return res if res is not None and res.status == "ok" else None


def _drawings(context):
    res = _ok(context, DRAWINGS)
    if res is None:
        return []
    out = []
    for f in res.outputs.get("files", []):
        if not f["path"].endswith(DRAWING_SUFFIXES):
            continue
        file = Path(context.work_dir or "") / res.outputs["directory"] / f["path"]
        out.append({"name": Path(f["path"]).stem, "title": f"Drawing {f['path']}", "path": f["path"], "code": None, "file": file, "recorded": f["sha256"],
                    "source": f"{res.outputs['directory']}/{f['path']}"})
    return out


def _documents(context):
    res = _ok(context, DOCUMENTS)
    docs = res.outputs.get("documents", []) if res is not None else []
    return [{"name": d["name"], "title": d["name"].replace("_", " ").capitalize(), "path": None, "code": None, "file": None, "recorded": d["sha256"], "source": None}
            for d in docs]


def deliverables(context):
    return _drawings(context) + _documents(context)


def apply_names(items, names, project_code):
    """Give every deliverable its document code and, for a drawing file, its path inside the transmittal, from `engine_inputs.deliverable_names`.

    `names` is {engine name: naming entry} (see `naming.py`). A deliverable without an entry, an invalid entry, a project code that is not
    AAAA-PROVIDER-CLIENT-CODE or two files with one path stop the stage: no name is invented.
    """
    code_ok = bool(naming.PROJECT_CODE.fullmatch(project_code or ""))
    errors = [] if code_ok else [f"the project code {project_code!r} must be AAAA-PROVIDER-CLIENT-CODE to name deliverables"]
    names = names if isinstance(names, dict) else {}
    for item in items:
        entry = names.get(item["name"])
        bad = ["no entry in engine_inputs.deliverable_names"] if entry is None else naming.problems(entry)
        errors += [f"{item['name']}: {b}" for b in bad]
        if bad or not code_ok:
            continue
        item["code"] = naming.document_code(project_code, entry)
        if item["file"] is not None:
            item["path"] = naming.file_path(project_code, entry, Path(item["path"]).suffix)
    paths = [i["path"] for i in items if i["path"]]
    errors += [f"two files share the path {p}" for p in sorted({p for p in paths if paths.count(p) > 1})]
    if errors:
        raise StageInputError(errors)


def _file_hash(item):
    """The SHA-256 of a deliverable; a drawing file must still match the hash stage 14 recorded."""
    if item["file"] is None:
        return item["recorded"]
    if not item["file"].is_file():
        raise StageInputError([f"{item['source']}: the drawing file recorded by stage 14 is missing"])
    sha = sha256_file(item["file"])
    if sha != item["recorded"]:
        raise StageInputError([f"{item['source']}: the file changed after stage 14 (hash differs from the recorded one)"])
    return sha


def _number(manifest):
    return int(TRANSMITTAL.fullmatch(manifest["transmittal"]).group(1))


def plan_transmittal(store, revision):
    """(transmittal id, previous, same): the id this run writes, the open manifest of another revision it supersedes (or None) and the unsigned draft of the
    same revision it replaces (or None). A signed or already superseded transmittal of this revision blocks."""
    existing = [m for _, m in store.read_manifests()]
    same = sorted((m for m in existing if m["revision"] == revision), key=_number)
    for m in same:
        if m["signed"] is not None:
            raise StageInputError([f"{m['transmittal']} (revision {revision}) is signed: use a new revision to regenerate it"])
        if m["superseded_by"] is not None:
            raise StageInputError([f"{m['transmittal']} (revision {revision}) is already superseded by {m['superseded_by']}: use a new revision"])
    if same:
        return same[-1]["transmittal"], None, same[-1]
    open_ones = sorted((m for m in existing if m["superseded_by"] is None), key=_number)
    nxt = max((_number(m) for m in existing), default=0) + 1
    return f"TR-{nxt:03d}", (open_ones[-1] if open_ones else None), None


class PackageIssueStage(Stage):
    """Stage 16: the manifest (`draft`) and the transmittal folder of the deliverables of this run."""

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
                                  findings=run_findings(context) + list(extra), review_status=DRAFT, norm_reader=lambda _p: records)
        except ManifestError as exc:
            raise StageInputError(exc.errors) from exc

    @staticmethod
    def _inputs(context):
        store = context.store
        return store.read_ssot("inputs_manifest.json") if store.is_frozen() else context.inputs_manifest

    def execute(self, context):
        store = context.store
        if store is None:
            return self._unavailable("no_store", "no project store: the manifest is written under .epc/manifests/ of a project folder")
        items = deliverables(context)
        if not items:
            return self._unavailable("no_deliverables", "no deliverable to issue: stages 14 and 15 produced no drawing file or document in this run")
        records = read_norm_records(sorted({c["function"].split(".")[0] for c in run_engine_calls(context)}))
        import epc_calc_check
        files, project, start = deliverable_bytes(items), engine_inputs_for_check(context), finding_count(context) + 1
        before = epc_calc_check.check_run(run_dict(context, LAST_PRODUCER), project=project, files=files, run_id=context.pipeline_run_id, start_id=start,
                                          groups=("documents",))
        names = (context.engine_inputs or {}).get("deliverable_names")
        if names is not None:
            apply_names(items, names, (context.profile or {}).get("project_code"))
        transmittal, previous, same = plan_transmittal(store, context.revision)
        rows = [{"name": i["name"], "title": i["title"], "code": i["code"], "path": i["path"], "sha256": _file_hash(i), "source": i["source"]} for i in items]
        manifest = self._manifest(context, transmittal, [{k: r[k] for k in ("name", "title", "code", "path", "sha256")} for r in rows], records, before)
        replaced = []
        if previous:
            old, manifest = supersede(previous, manifest)
            replaced.append({"path": store.manifest_rel(old), "manifest": old})
        elif same:
            manifest["supersedes"] = same["supersedes"]
        path = store.manifest_rel(manifest)
        copies = [{"source": i["source"], "to": f"deliverables/{transmittal}/{i['path']}"} for i in items if i["file"] is not None]
        not_verified = sum(1 for r in records if r["review_status"] != VERIFIED)
        outputs = {"revision": context.revision, "manifests": [{"path": path, "manifest": manifest}], "superseded": replaced, "copies": copies,
                   "norm_records": {"listed": len(records), "not_verified": not_verified},
                   "transmittal": {"id": transmittal, "project_code": (context.profile or {}).get("project_code"), "revision": context.revision,
                                   "pipeline_run_id": context.pipeline_run_id, "review_status": DRAFT, "manifest": path, "files": rows}}
        after = self._check_manifests(context, outputs, files, project, start + len(before))
        outputs["calc_check"] = {"findings_count": len(before) + len(after), "by_severity": by_severity(before + after)}
        longest = max((len(f"{store.root}/deliverables/{transmittal}/{r['path']}") for r in rows if r["path"]), default=0)
        outputs["naming"] = {"named": names is not None, "longest_path": longest}
        msg = f"transmittal {transmittal} (revision {context.revision}): {len(rows)} file(s), draft; {not_verified} of {len(records)} norm records not verified"
        if longest > naming.PATH_WARNING:
            msg += f"; WARNING: a file path has {longest} characters (Windows stops at about 260): shorten the project folder or the descriptions"
        return self.result("ok", outputs=outputs, findings=before + after, message=msg)

    @staticmethod
    def _check_manifests(context, outputs, files, project, start):
        """calc_check on the manifest just built (it cannot carry the findings about itself)."""
        import epc_calc_check
        run = run_dict(context, LAST_PRODUCER)
        run["results"].append({"stage": 16, "status": "ok", "outputs": outputs, "findings": []})
        return epc_calc_check.check_run(run, project=project, files=files, run_id=context.pipeline_run_id, start_id=start, groups=("manifests",))
