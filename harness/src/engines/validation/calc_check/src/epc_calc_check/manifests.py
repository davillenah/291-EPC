"""Group "manifests": the transmittal manifest of stage 16 (or given in `files` as JSON bytes) against the schema, the revision labels, the hashes recorded
by stages 14 and 15 and the bytes of the files.

The schema is `project["manifest_schema"]` when given; otherwise it is read at call time from `harness/schemas/deliverable_manifest.schema.json` found by walking up
from this file. If neither exists the schema check is reported as a note, never skipped silently.
"""
import json
import re
from pathlib import Path

from epc_calc_check import view as V
from epc_calc_check._values import is_sha256
from epc_calc_check.findings import issue
from epc_calc_check.schema import validate

SCHEMA_NAME = "deliverable_manifest.schema.json"
REVISION = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,15}")
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
MANIFEST_SUFFIX = ".manifest.json"


def load_schema(view):
    given = view.project.get("manifest_schema")
    if isinstance(given, dict):
        return given
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "harness" / "schemas" / SCHEMA_NAME
        if candidate.is_file():
            return json.loads(candidate.read_text(encoding="utf-8"))
    return None


def collect(view):
    """[(path, manifest dict)] from stage 16 and from `files` entries that end in .manifest.json (bytes or str of JSON)."""
    found = [(m.get("path", "?"), m.get("manifest")) for m in view.outputs(16).get("manifests") or [] if isinstance(m, dict)]
    for path, data in view.files.items():
        if isinstance(path, str) and path.endswith(MANIFEST_SUFFIX) and isinstance(data, (bytes, bytearray, str)):
            try:
                found.append((path, json.loads(data)))
            except ValueError:
                found.append((path, None))
    return found


def _schema_issues(path, manifest, schema):
    if not isinstance(manifest, dict):
        return [issue("CC-F10", "package_issue", path, manifest, "a manifest object", "Rewrite the manifest.", "manifest")]
    return [issue("CC-F10", "package_issue", f"{path}{err.split(':')[0][1:]}", err.split(": ", 1)[1], "valid against the manifest schema", "Rebuild the manifest.", f"{SCHEMA_NAME}: {err}")
            for err in validate(manifest, schema)]


def _labels(view, path, manifest):
    out = []
    if not isinstance(manifest, dict):
        return out
    rev, run = manifest.get("revision"), manifest.get("pipeline_run_id")
    if not (isinstance(rev, str) and REVISION.fullmatch(rev)):
        out.append(issue("CC-F11", "package_issue", f"{path}/revision", rev, "a revision label such as R0", "Use a valid revision label.", "manifest"))
    elif view.outputs(16).get("revision") not in (None, rev):
        out.append(issue("CC-F11", "package_issue", f"{path}/revision", rev, view.outputs(16).get("revision"), "The manifest carries the revision of its issue.", "stage 16 revision"))
    if not (isinstance(run, str) and RUN_ID.fullmatch(run)):
        out.append(issue("CC-F11", "package_issue", f"{path}/pipeline_run_id", run, "a valid run id", "Use a valid run id.", "manifest"))
    elif view.run.get("pipeline_run_id") not in (None, run):
        out.append(issue("CC-F11", "package_issue", f"{path}/pipeline_run_id", run, view.run.get("pipeline_run_id"), "A manifest names the run that produced it.", "run_result"))
    return out


def _recorded(view, entry):
    """The hash stage 14 or 15 recorded for the file `entry` of a manifest, or None."""
    if entry.get("path"):
        files = {Path(str(f.get("path"))).stem: f.get("sha256") for f in view.outputs(14).get("files") or [] if isinstance(f, dict) and str(f.get("path")).endswith(".dxf")}
        return files.get(entry.get("name"))
    for d in view.outputs(15).get("documents") or []:
        if isinstance(d, dict) and d.get("name") == entry.get("name"):
            return d.get("sha256")
    return None


def _sources(view):
    """{path of the file inside the transmittal: key of its bytes in `files`} from the stage 16 transmittal list."""
    rows = (view.outputs(16).get("transmittal") or {}).get("files") or []
    return {r.get("name"): r.get("source") for r in rows if isinstance(r, dict)}


def _hash_issues(view, path, manifest, sources):
    out = []
    entries = manifest.get("files")
    for n, entry in enumerate(entries if isinstance(entries, list) else []):
        if not isinstance(entry, dict):
            continue
        sha, where = entry.get("sha256"), f"{path}/files/{n}/sha256"
        recorded, source = _recorded(view, entry), sources.get(entry.get("name"))
        if recorded is not None and sha != recorded:
            out.append(issue("CC-D06", "package_issue", where, sha, recorded, "The manifest must carry the hash recorded when the deliverable was produced.", "stage 14/15 recorded hash"))
        if source in view.files and V.sha256_of(view.files[source]) != sha:
            out.append(issue("CC-D06", "package_issue", where, sha, V.sha256_of(view.files[source]), "The file differs from the hash in its manifest.", "SHA-256 of the file bytes"))
        if sha is not None and not is_sha256(sha):
            out.append(issue("CC-F06", "package_issue", where, sha, "64 lowercase hexadecimal characters", "Recompute the hash.", "manifest"))
    return out


def check_manifests(view):
    schema, sources = load_schema(view), _sources(view)
    manifests = collect(view)
    if manifests and schema is None:
        yield issue("CC-D07", "package_issue", "manifest_schema", None, None, "None.", "the manifest schema was not found, so the manifests were not validated")
    for path, manifest in manifests:
        if schema is not None:
            yield from _schema_issues(path, manifest, schema)
        if isinstance(manifest, dict):
            yield from _labels(view, path, manifest)
            yield from _hash_issues(view, path, manifest, sources)
