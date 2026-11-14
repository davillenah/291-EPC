"""The manifest of one transmittal (PRD section 13, schema `deliverable_manifest.schema.json`). Pure: it builds and checks dicts and writes nothing.

Writing is done by `ProjectStore.write_manifest` / `update_manifest` (store.py), which need the pipeline token; the run recorder calls them.

Where each field comes from:
  inputs            the frozen inputs manifest (`ssot/inputs_manifest.json`): every input file with its SHA-256 (not only the ones a deliverable used)
  engines           name and version of every engine in the recorded `engine_calls` (a version the engine does not expose is an error)
  normative_profile revisions from the project profile; norm records from `norm_records.read_norm_records` for the packages of those calls
  files             every file of the transmittal: name, title, path inside `deliverables/<transmittal>/` (null while a document has no rendered file) and SHA-256
  review_status     `draft` unless the caller asks otherwise; `approved_for_construction` raises `ApprovalBlocked` while a listed norm record is not
                    `verified` (D21). The schema repeats the rule, so a written manifest cannot break it either.
  mode              `edit` only when the package was made in edit mode (ADR-0035); a production manifest has no `mode`, as it never had
  signed            always None here: a signature is a human act. `supersede` moves a previous signature to `superseded_signature`.

No clock is read: equal inputs give equal manifests.
"""
import copy
import hashlib
from pathlib import Path

from disciplines.electrical_lv.intake.schema_check import load_schema, validate
from disciplines.electrical_lv.norm_records import VERIFIED, read_norm_records

SCHEMA = "deliverable_manifest.schema.json"
DRAFT, FOR_REVIEW, APPROVED = "draft", "for_review", "approved_for_construction"
SUFFIX = ".manifest.json"


class ManifestError(ValueError):
    """A manifest that cannot be built or is not valid. `errors` lists every reason."""

    def __init__(self, errors):
        errors = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("; ".join(errors))
        self.errors = errors


class ApprovalBlocked(ManifestError):
    """`approved_for_construction` was asked while a norm record is not verified (D21)."""


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reference(manifest):
    """`<transmittal>/<revision>`: how `supersedes` and `superseded_by` name a manifest."""
    return f"{manifest['transmittal']}/{manifest['revision']}"


def manifest_name(manifest):
    return manifest["transmittal"] + SUFFIX


def engines_of(engine_calls):
    """[{name, version}] unique and sorted; a call without a version is an error (no value is invented)."""
    seen = set()
    for call in engine_calls:
        if not call.get("version"):
            raise ManifestError(f"engine {call.get('engine')!r} exposes no version")
        seen.add((call["engine"], str(call["version"])))
    return [{"name": n, "version": v} for n, v in sorted(seen)]


def packages_of(engine_calls):
    """Top-level engine packages named by the recorded function paths (`epc_aea90364.board_memo.build` -> `epc_aea90364`)."""
    return sorted({call["function"].split(".")[0] for call in engine_calls})


def inputs_of(inputs_manifest):
    if not inputs_manifest or "files" not in inputs_manifest:
        raise ManifestError("the frozen inputs manifest is missing")
    return [{"path": f["path"], "sha256": f["sha256"]} for f in sorted(inputs_manifest["files"], key=lambda f: f["path"])]


def unverified(records):
    return [r["id"] for r in records if r["review_status"] != VERIFIED]


def check_approval(review_status, records):
    """D21: raises `ApprovalBlocked` when approval is asked while any listed record is not verified."""
    bad = unverified(records) if review_status == APPROVED else []
    if bad:
        shown = ", ".join(bad[:5]) + (" ..." if len(bad) > 5 else "")
        raise ApprovalBlocked(f"cannot approve for construction: {len(bad)} norm record(s) not verified ({shown})")


def mode_field(mode):
    """{"mode": "edit"} for a package made in edit mode (ADR-0035: norm records not verified did not stop it, and it is not for production); nothing for production."""
    return {"mode": "edit"} if mode == "edit" else {}


def check(manifest):
    """Schema errors of a manifest (empty list = valid)."""
    return validate(manifest, load_schema(SCHEMA))


def files_of(files):
    """The `files` list of a manifest: [{name, title, code, path, sha256}] sorted by name; duplicate names are an error."""
    names = [f["name"] for f in files]
    if len(set(names)) != len(names):
        raise ManifestError("two files of one transmittal share a name")
    return [{"name": f["name"], "title": f["title"], "code": f.get("code"), "path": f["path"], "sha256": f["sha256"]} for f in sorted(files, key=lambda f: f["name"])]


def build_manifest(*, transmittal, title, revision, run_id, inputs_manifest, engine_calls, normative_profile, findings, files,
                   review_status=DRAFT, norm_reader=read_norm_records, mode="production"):
    """The manifest dict of one transmittal; raises `ManifestError` (or `ApprovalBlocked`) instead of returning a wrong one.

    `files` is [{name, title, path, sha256}] (see `files_of`). `normative_profile` is the profile's `normative_profile` (its `revisions` are copied).
    `norm_reader(packages)` returns the norm records with their review state; tests inject a stub, the default reads the engines' registers.
    """
    records = norm_reader(packages_of(engine_calls))
    check_approval(review_status, records)
    manifest = {
        "transmittal": transmittal, "title": title, "revision": revision, "pipeline_run_id": run_id,
        "inputs": inputs_of(inputs_manifest), "engines": engines_of(engine_calls),
        "normative_profile": {"revisions": copy.deepcopy((normative_profile or {}).get("revisions") or {}), "norm_records": copy.deepcopy(records)},
        "files": files_of(files), "findings": copy.deepcopy(findings), "review_status": review_status,
        "signed": None, "superseded_signature": None, "supersedes": None, "superseded_by": None}
    manifest.update(mode_field(mode))
    errors = check(manifest)
    if errors:
        raise ManifestError(errors)
    return manifest


def supersede(previous, new):
    """(previous', new'): the earlier manifest marked as replaced by the new one. Inputs are not modified.

    The earlier transmittal's signature (if any) moves to `superseded_signature` and `signed` becomes null; `new.supersedes` names the earlier one.
    """
    if previous["transmittal"] == new["transmittal"]:
        raise ManifestError("a transmittal is superseded by a later transmittal, not by itself")
    if previous["revision"] == new["revision"]:
        raise ManifestError(f"{reference(previous)}: the new manifest needs a different revision")
    if previous["superseded_by"] is not None:
        raise ManifestError(f"{reference(previous)} is already superseded by {previous['superseded_by']}")
    old, fresh = copy.deepcopy(previous), copy.deepcopy(new)
    old["superseded_by"] = reference(new)
    if old["signed"] is not None:
        old["superseded_signature"], old["signed"] = old["signed"], None
    fresh["supersedes"] = reference(previous)
    for item in (old, fresh):
        errors = check(item)
        if errors:
            raise ManifestError(errors)
    return old, fresh
