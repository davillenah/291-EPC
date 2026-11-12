"""Stage 16 (package issue): one manifest per deliverable the earlier stages of this run produced, plus a transmittal list (MIG-32).

The stage is pure: it builds the manifests (`manifest.py`) and returns them in `outputs`; the run recorder (which holds the store's write token)
writes them under `deliverables/<revision>/` through `ProjectStore.write_manifest` / `update_manifest`.

What counts as a deliverable today:
  - drawings: the `.dxf` files of stage 14 (`.svg` is not a deliverable; the `.json` and `.md` files of the engine's output folder are internal);
  - documents: the structured documents of stage 15, whose hash is the one stage 15 recorded (no rendered file exists yet).

Before the manifests are built the stage runs the cross-document checks of `epc_calc_check` (groups `documents`: memo against stages, hashes, drawing summary,
file bytes) and the findings join the ones every manifest carries; after they are built it checks the manifests themselves (schema, labels, hashes against the
recorded ones and the file bytes). Those second findings are reported by the stage and counted in `outputs["calc_check"]`; they cannot be inside the
manifests they describe. The stage never fails because of a finding.

Everything is `draft`: the stage never approves, never signs and never changes a norm review state. With no project store, or with no
deliverable, it returns `not_available` with the reason. Limitations: `inputs`, `engines`, `findings` and the norm records are those of the whole run
up to stage 15, not only what one deliverable used (the stage outputs do not carry that mapping).
"""
import copy
import re
from pathlib import Path

from disciplines.electrical_lv.manifest import DRAFT, ManifestError, build_manifest, supersede
from disciplines.electrical_lv.norm_records import VERIFIED, read_norm_records
from disciplines.electrical_lv.stages.base import Stage, StageInputError
from disciplines.electrical_lv.stages.calc_check_stage import by_severity, engine_inputs_for_check, run_dict

DRAWINGS, DOCUMENTS, LAST_PRODUCER = 14, 15, 15
DRAWING_SUFFIXES = (".dxf",)
SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


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


def _drawings(context, project):
    res = _ok(context, DRAWINGS)
    if res is None:
        return []
    out = []
    for f in res.outputs.get("files", []):
        if not f["path"].endswith(DRAWING_SUFFIXES):
            continue
        stem = Path(f["path"]).stem
        file = Path(context.work_dir or "") / res.outputs["directory"] / f["path"]
        out.append({"id": SAFE.sub("-", f"{project}-DRW-{stem}"), "title": f"Drawing {f['path']}", "file": file, "recorded": f["sha256"],
                    "source": f"{res.outputs['directory']}/{f['path']}"})
    return out


def _documents(context, project):
    res = _ok(context, DOCUMENTS)
    docs = res.outputs.get("documents", []) if res is not None else []
    return [{"id": SAFE.sub("-", f"{project}-DOC-{d['name']}"), "title": d["name"].replace("_", " ").capitalize(), "file": None,
             "recorded": d["sha256"], "source": None} for d in docs]


def deliverables(context):
    project = (context.profile or {}).get("project_code") or ""
    return _drawings(context, project) + _documents(context, project)


def _hash_args(item):
    """(deliverable_file, output_sha256) for build_manifest; a drawing file must still match the hash stage 14 recorded."""
    if item["file"] is None:
        return None, item["recorded"]
    if not item["file"].is_file():
        raise StageInputError([f"{item['source']}: the drawing file recorded by stage 14 is missing"])
    return item["file"], None


def _previous(store, manifest):
    """The latest manifest of the same deliverable_id and another revision that is not superseded yet, or None. A signed twin of this revision blocks."""
    others = []
    for rel, old in store.read_manifests(manifest["deliverable_id"]):
        if old["revision"] == manifest["revision"]:
            if old["signed"] is not None:
                raise StageInputError([f"{rel} is signed: use a new revision to regenerate it"])
        elif old["superseded_by"] is None:
            others.append((rel, old))
    return others[-1] if others else None


class PackageIssueStage(Stage):
    """Stage 16: manifests (all `draft`) and the transmittal of the deliverables of this run."""

    wired = True
    wiring_task = "MIG-32"

    def _unavailable(self, reason, message):
        return self.result("not_available", message=message, reason=reason)

    def _manifest(self, context, item, records, extra=()):
        file, recorded = _hash_args(item)
        try:
            manifest = build_manifest(file, deliverable_id=item["id"], title=item["title"], revision=context.revision, run_id=context.pipeline_run_id,
                                      inputs_manifest=self._inputs(context), engine_calls=run_engine_calls(context),
                                      normative_profile=(context.profile or {}).get("normative_profile"), findings=run_findings(context) + list(extra),
                                      review_status=DRAFT, output_sha256=recorded if file is None else None, norm_reader=lambda _p: records)
        except ManifestError as exc:
            raise StageInputError(exc.errors) from exc
        if file is not None and manifest["output_sha256"] != item["recorded"]:
            raise StageInputError([f"{item['source']}: the file changed after stage 14 (hash differs from the recorded one)"])
        return manifest

    @staticmethod
    def _inputs(context):
        store = context.store
        return store.read_ssot("inputs_manifest.json") if store.is_frozen() else context.inputs_manifest

    def execute(self, context):
        store = context.store
        if store is None:
            return self._unavailable("no_store", "no project store: manifests are written under deliverables/<revision>/ of a project folder")
        items = deliverables(context)
        if not items:
            return self._unavailable("no_deliverables", "no deliverable to issue: stages 14 and 15 produced no drawing file or document in this run")
        records = read_norm_records(sorted({c["function"].split(".")[0] for c in run_engine_calls(context)}))
        import epc_calc_check
        files, project, start = deliverable_bytes(items), engine_inputs_for_check(context), finding_count(context) + 1
        before = epc_calc_check.check_run(run_dict(context, LAST_PRODUCER), project=project, files=files, run_id=context.pipeline_run_id, start_id=start,
                                          groups=("documents",))
        manifests, replaced, rows = [], [], []
        for item in items:
            new = self._manifest(context, item, records, before)
            prev = _previous(store, new)
            if prev:
                old, new = supersede(prev[1], new)
                replaced.append({"path": prev[0], "manifest": old})
            path = store.manifest_rel(new)
            manifests.append({"path": path, "manifest": new})
            rows.append({"deliverable_id": new["deliverable_id"], "title": new["title"], "revision": new["revision"], "source": item["source"],
                         "output_sha256": new["output_sha256"], "manifest": path, "review_status": new["review_status"]})
        not_verified = sum(1 for r in records if r["review_status"] != VERIFIED)
        outputs = {"revision": context.revision, "manifests": manifests, "superseded": replaced,
                   "norm_records": {"listed": len(records), "not_verified": not_verified},
                   "transmittal": {"project_code": (context.profile or {}).get("project_code"), "revision": context.revision,
                                   "pipeline_run_id": context.pipeline_run_id, "review_status": DRAFT, "deliverables": rows}}
        after = self._check_manifests(context, outputs, files, project, start + len(before))
        outputs["calc_check"] = {"findings_count": len(before) + len(after), "by_severity": by_severity(before + after)}
        msg = f"{len(manifests)} manifest(s) for revision {context.revision}, all draft; {not_verified} of {len(records)} norm records not verified"
        return self.result("ok", outputs=outputs, findings=before + after, message=msg)

    @staticmethod
    def _check_manifests(context, outputs, files, project, start):
        """calc_check on the manifests just built (they cannot carry the findings about themselves)."""
        import epc_calc_check
        run = run_dict(context, LAST_PRODUCER)
        run["results"].append({"stage": 16, "status": "ok", "outputs": outputs, "findings": []})
        return epc_calc_check.check_run(run, project=project, files=files, run_id=context.pipeline_run_id, start_id=start, groups=("manifests",))
