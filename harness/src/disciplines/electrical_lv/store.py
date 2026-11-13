"""The project folder and its single-source-of-truth (SSOT) files (PRD sections 10.3 and 14.4).

Layout of `projects/<code>/`: `project_profile.json`, `master_project_state.json`, `epc-progress.txt`, `inputs/` (immutable after
intake, hashed), `ssot/` (project data), `runs/<pipeline_run_id>/`, `deliverables/<rev>/`, `reviews/`, `transmittals/`, `audit/`.

SSOT write rule. Every method that writes the profile, the state, the progress log, `ssot/` or a run folder takes a
`PipelineToken` as its first argument. A token can only be created by `ProjectStore.pipeline_session()`, which only
`pipeline.run()` calls (an architecture test checks it): the constructor of `PipelineToken` refuses to work without a private
module-level sentinel, so other code cannot write by accident. A token is bound to one project folder and is dead when the
session ends. This is a guard against accidents and against agents calling the wrong function, not a security boundary
(Python cannot hide a module-level object from code that is determined to reach it).

Other rules enforced here: no write outside the project folder (absolute paths, `..` and backslashes are refused, symlinks
are resolved); `inputs/` cannot be written once `ssot/inputs_manifest.json` exists (inputs are frozen); files are written
atomically (temp file + replace) and deterministically (sorted keys, indent 2, UTF-8, LF, trailing newline). Nothing here reads
the clock: timestamps are injected by the caller.

Deliverable manifests (`deliverables/<rev>/<id>.manifest.json`, MIG-32) are written by `write_manifest` / `update_manifest` with the same token; an
update can only mark a manifest as superseded. Only this module may write files under `harness/src/disciplines` (the drawing engine writes
stage 14's files itself, under the work_dir).
"""
import contextlib
import json
import os
import re
import shutil
from pathlib import Path

from disciplines.electrical_lv.intake.hashing import build_manifest, verify_inputs
from disciplines.electrical_lv.intake.profile import TEMPLATE
from disciplines.electrical_lv.intake.schema_check import load_schema, validate
from disciplines.electrical_lv.stages.base import make_finding

PROFILE = "project_profile.json"
STATE = "master_project_state.json"
PROGRESS = "epc-progress.txt"
MANIFEST_SCHEMA = "deliverable_manifest.schema.json"
MANIFEST_SUFFIX = ".manifest.json"
SUPERSEDE_FIELDS = ("superseded_by", "signed", "superseded_signature")
MANIFEST_NAME = "inputs_manifest.json"
WORKFLOW = "workflow.json"
ANSWERS = "intake_answers.json"
WORKFLOW_STATES = ("init", "intake_done", "running", "draft_ready", "in_review", "corrected", "approved", "issued")
WORKFLOW_ENTRY = ("from", "to", "transition", "role", "actor_id", "pipeline_run_id")
SUBDIRS = ("inputs", "ssot", "runs", "deliverables", "reviews", "transmittals", "audit")
TEMPLATE_DIR = TEMPLATE.parent
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
_DRIVE = re.compile(r"^[A-Za-z]:")
_MINT = object()


class StoreError(ValueError):
    """A write or read the store refuses. `errors` lists every reason."""

    def __init__(self, errors):
        errors = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("; ".join(errors))
        self.errors = errors


class PipelineToken:
    """Proof that the caller is a running pipeline. Create it only through `ProjectStore.pipeline_session()`."""

    __slots__ = ("run_id", "_root", "_open")

    def __init__(self, run_id, root, _mint=None):
        if _mint is not _MINT:
            raise PermissionError("a PipelineToken can only be created by ProjectStore.pipeline_session(), used by pipeline.run()")
        self.run_id = run_id
        self._root = root
        self._open = True

    @property
    def is_open(self):
        return self._open


def dumps(data):
    """Deterministic JSON text: sorted keys, indent 2, UTF-8 characters kept, LF, trailing newline."""
    try:
        return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    except (TypeError, ValueError) as exc:
        raise StoreError(f"data is not plain JSON: {exc}") from exc


def atomic_write(target, data):
    """Write bytes to `target` through a temp file in the same folder and `os.replace`; no temp file is left behind."""
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp")
    try:
        with open(tmp, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, target)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def clean_parts(rel):
    """The components of a relative POSIX path; absolute paths, drive letters, backslashes, empty, `.` and `..` are refused."""
    if not isinstance(rel, str) or not rel:
        raise StoreError(f"path must be a non-empty string, got {rel!r}")
    if rel.startswith("/") or "\\" in rel or _DRIVE.match(rel) or "\x00" in rel:
        raise StoreError(f"path {rel!r} must be relative and use '/'")
    parts = rel.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise StoreError(f"path {rel!r} must not contain empty, '.' or '..' components")
    return parts


def check_run_id(run_id):
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise StoreError(f"pipeline_run_id {run_id!r} must match {RUN_ID.pattern}")
    return run_id


def workflow_problems(data):
    """Reasons a workflow record is invalid (empty list = valid): {'state': <state>, 'history': [{from, to, transition, role, actor_id, pipeline_run_id}]}."""
    if not isinstance(data, dict) or sorted(data) != ["history", "state"]:
        return ["workflow: expected exactly the keys 'state' and 'history'"]
    problems = [] if data["state"] in WORKFLOW_STATES else [f"workflow.state: {data['state']!r} is not a state"]
    if not isinstance(data["history"], list):
        return problems + ["workflow.history: must be a list"]
    for n, entry in enumerate(data["history"]):
        ok = isinstance(entry, dict) and sorted(entry) == sorted(WORKFLOW_ENTRY) and all(isinstance(v, str) for v in entry.values())
        if not ok or entry["from"] not in WORKFLOW_STATES or entry["to"] not in WORKFLOW_STATES:
            problems.append(f"workflow.history[{n}]: needs the string fields {WORKFLOW_ENTRY} and known states")
    return problems


def _inside(path, base):
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


class ProjectStore:
    """One project folder. Reads are free; writes need a `PipelineToken` (see the module docstring)."""

    def __init__(self, project_dir):
        self.root = Path(project_dir).resolve()

    # -- paths ---------------------------------------------------------------------------------------------------------------
    @property
    def inputs_dir(self):
        return self.root / "inputs"

    def resolve(self, rel, under=""):
        """Absolute path of `rel` below `<root>/<under>`; raises StoreError when it would leave that folder."""
        base = (self.root / under).resolve() if under else self.root
        target = base.joinpath(*clean_parts(rel)).resolve()
        if not _inside(target, base):
            raise StoreError(f"path {rel!r} leaves the project folder")
        return target

    def is_frozen(self):
        return (self.root / "ssot" / MANIFEST_NAME).is_file()

    # -- creation (the /init flow; the pipeline is not involved) -----------------------------------------------------------
    def init_from_template(self, template_dir=None):
        """Copy the template structure into this (new or empty) folder. READMEs of the template are not copied."""
        template = Path(template_dir or TEMPLATE_DIR).resolve()
        if _inside(self.root, TEMPLATE_DIR.resolve()):
            raise StoreError("refusing to write inside the repository template projects/_template")
        if self.root.exists() and any(self.root.iterdir()):
            raise StoreError(f"{self.root} is not empty: a project can only be created in a new or empty folder")
        self.root.mkdir(parents=True, exist_ok=True)
        for name in SUBDIRS:
            (self.root / name).mkdir(exist_ok=True)
        for src in sorted(template.rglob("*")):
            self._copy_template_entry(template, src)

    def _copy_template_entry(self, template, src):
        dst = self.root / src.relative_to(template)
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        elif src.name != "README.md":
            shutil.copyfile(src, dst)

    def init_with_answers(self, answers, template_dir=None):
        """The `/init` flow (MIG-33b): the template structure plus the validated form answers as `inputs/intake_answers.json`.

        The answers are an input like any other: hashed with the rest of `inputs/` when stage 1 freezes them. Stage 1 builds the profile from them.
        """
        self.init_from_template(template_dir)
        self.write_input(ANSWERS, dumps(answers))

    def write_input(self, rel, content):
        """Add an input file (bytes or text) at intake time. Refused once the inputs are frozen."""
        if self.is_frozen():
            raise StoreError("inputs are frozen: they are immutable after intake")
        data = content if isinstance(content, bytes) else str(content).encode("utf-8")
        atomic_write(self.resolve(rel, "inputs"), data)

    # -- token ---------------------------------------------------------------------------------------------------------------
    @contextlib.contextmanager
    def pipeline_session(self, run_id):
        """Open a write session for one pipeline run. Used by `pipeline.run()` only."""
        token = PipelineToken(check_run_id(run_id), self.root, _mint=_MINT)
        try:
            yield token
        finally:
            token._open = False

    def _require(self, token):
        ok = isinstance(token, PipelineToken) and token._root == self.root and token.is_open
        if not ok:
            raise PermissionError("this write needs an open PipelineToken of this project, which only pipeline.run() obtains")

    # -- writes (all need the token) -----------------------------------------------------------------------------------------
    def _write_json(self, rel, data, under=""):
        atomic_write(self.resolve(rel, under), dumps(data).encode("utf-8"))

    def _write_checked(self, token, name, data, schema_name):
        self._require(token)
        errors = validate(data, load_schema(schema_name))
        if errors:
            raise StoreError([f"{name}: {e}" for e in errors])
        self._write_json(name, data)

    def write_profile(self, token, profile):
        self._write_checked(token, PROFILE, profile, "project_profile.schema.json")

    def write_state(self, token, state):
        self._write_checked(token, STATE, state, "master_project_state.schema.json")

    def append_progress(self, token, line):
        """Append one line (no line break inside) to `epc-progress.txt`."""
        self._require(token)
        if not isinstance(line, str) or "\n" in line or "\r" in line:
            raise StoreError("a progress entry is one line of text")
        with open(self.resolve(PROGRESS), "ab") as handle:
            handle.write(line.encode("utf-8") + b"\n")

    def write_ssot(self, token, name, data):
        """Write `ssot/<name>` (a `.json` name, may include sub-folders). The inputs manifest is written only by `freeze_inputs`."""
        self._require(token)
        if not isinstance(name, str) or not name.endswith(".json"):
            raise StoreError(f"ssot file {name!r} must be a .json file")
        if name == MANIFEST_NAME:
            raise StoreError(f"{MANIFEST_NAME} is written only by freeze_inputs")
        self._write_json(name, data, "ssot")

    def write_workflow(self, token, data):
        """Write `reviews/workflow.json` (the lifecycle state of the project, MIG-33a). The record is validated by hand first."""
        self._require(token)
        problems = workflow_problems(data)
        if problems:
            raise StoreError(problems)
        self._write_json(WORKFLOW, data, "reviews")

    def write_review(self, token, name, data):
        """Write `reviews/<name>` (a `.json` name other than the workflow record): corrections recorded through the workflow (MIG-33b)."""
        self._require(token)
        if not isinstance(name, str) or not name.endswith(".json") or name == WORKFLOW:
            raise StoreError(f"review file {name!r} must be a .json file other than {WORKFLOW}")
        self._write_json(name, data, "reviews")

    def make_run_dir(self, token, run_id):
        """Create `runs/<run_id>/` and return its path (the folder the drawing stage writes into)."""
        self._require(token)
        path = self.resolve(check_run_id(run_id), "runs")
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    def manifest_rel(self, manifest):
        """`deliverables/<revision>/<deliverable_id>.manifest.json` of a manifest (checked against the schema first)."""
        errors = validate(manifest, load_schema(MANIFEST_SCHEMA))
        if errors:
            raise StoreError([f"manifest: {e}" for e in errors])
        return f"deliverables/{manifest['revision']}/{manifest['deliverable_id']}{MANIFEST_SUFFIX}"

    def write_manifest(self, token, manifest):
        """Write a new deliverable manifest under `deliverables/<revision>/`; returns its relative path.

        Refuses an invalid manifest and refuses to overwrite a manifest that carries a signature (a signature is only ever moved by `update_manifest`).
        """
        self._require(token)
        rel = self.manifest_rel(manifest)
        target = self.resolve(rel)
        if target.is_file() and json.loads(target.read_text(encoding="utf-8")).get("signed") is not None:
            raise StoreError(f"{rel} is signed and cannot be overwritten")
        self._write_json(rel, manifest)
        return rel

    def update_manifest(self, token, manifest):
        """Mark an existing manifest as superseded: only `superseded_by`, `signed` and `superseded_signature` may differ from the stored one.

        A signature can only be moved to `superseded_signature` (never created, edited or dropped) and `superseded_by` can only be set once.
        """
        self._require(token)
        rel = self.manifest_rel(manifest)
        old = self.read_json(rel)
        changed = sorted(k for k in set(old) | set(manifest) if k not in SUPERSEDE_FIELDS and old.get(k) != manifest.get(k))
        problems = [f"{k}: cannot change in an update" for k in changed]
        if old["superseded_by"] is not None and manifest["superseded_by"] != old["superseded_by"]:
            problems.append("superseded_by: already set")
        moved = manifest["signed"] is None and old["signed"] is not None and manifest["superseded_signature"] == old["signed"]
        if (manifest["signed"], manifest["superseded_signature"]) != (old["signed"], old["superseded_signature"]) and not (moved and old["superseded_signature"] is None):
            problems.append("signed: can only be moved to superseded_signature")
        if problems:
            raise StoreError([f"{rel}: {p}" for p in problems])
        self._write_json(rel, manifest)
        return rel

    def freeze_inputs(self, token):
        """Hash `inputs/` into `ssot/inputs_manifest.json`; from then on the inputs are immutable. Returns the manifest."""
        self._require(token)
        if self.is_frozen():
            raise StoreError("inputs are already frozen")
        manifest = build_manifest(self.inputs_dir)
        self._write_json(MANIFEST_NAME, manifest, "ssot")
        return manifest

    # -- reads ---------------------------------------------------------------------------------------------------------------
    def read_json(self, rel, under=""):
        path = self.resolve(rel, under)
        if not path.is_file():
            raise StoreError(f"{rel} does not exist")
        return json.loads(path.read_text(encoding="utf-8"))

    def read_profile(self):
        return self.read_json(PROFILE)

    def read_state(self):
        return self.read_json(STATE)

    def read_ssot(self, name):
        return self.read_json(name, "ssot")

    def read_manifests(self, deliverable_id=None):
        """[(relative path, manifest)] of every manifest under `deliverables/`, sorted by path; optionally only one deliverable_id."""
        base = self.root / "deliverables"
        out = []
        for path in sorted(base.glob("*/*" + MANIFEST_SUFFIX)) if base.is_dir() else []:
            data = json.loads(path.read_text(encoding="utf-8"))
            if deliverable_id is None or data.get("deliverable_id") == deliverable_id:
                out.append((path.relative_to(self.root).as_posix(), data))
        return out

    def read_workflow(self):
        """The workflow record, or None when the project has none yet."""
        path = self.resolve(WORKFLOW, "reviews")
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def read_answers(self):
        """The form answers kept by `init_with_answers`, or None when the project has none."""
        path = self.resolve(ANSWERS, "inputs")
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def list_reviews(self):
        """Names of the files below `reviews/` other than the workflow record, sorted."""
        base = self.root / "reviews"
        return sorted(p.name for p in base.glob("*.json") if p.name != WORKFLOW) if base.is_dir() else []

    def read_progress(self):
        return self.resolve(PROGRESS).read_text(encoding="utf-8")

    def run_dir_of_stage(self, number):
        """`runs/<id>/` of the last run that finished stage `number` ok (where its files were written), or None."""
        for line in reversed(self.read_progress().splitlines()):
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4 and parts[1].startswith("run ") and parts[2].startswith(f"stage {number} ") and parts[3] == "ok":
                path = self.resolve(check_run_id(parts[1][4:]), "runs")
                return str(path) if path.is_dir() else None
        return None

    def verify_inputs_unchanged(self, run_id="run-0"):
        """Blocking findings (rule IM-01), one per input file that changed, disappeared or appeared since the freeze."""
        if not self.is_frozen():
            raise StoreError("inputs are not frozen yet")
        problems = verify_inputs(self.read_ssot(MANIFEST_NAME), self.inputs_dir)
        return [make_finding(n, run_id, "pipeline", f"inputs/{p['path']}", p["problem"], "unchanged since intake", "IM-01",
                             "Restore the input file or open a new project revision.") for n, p in enumerate(problems, start=1)]
