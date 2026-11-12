"""Shared helpers of the synthetic-project integration tests (MIG-3X): run `synthetic_lv_small` through the real `epc` CLI in a temp projects root.

Not a test module. The project is read from `harness/tests/golden_projects/synthetic_lv_small/` (invented data only); everything the run writes goes
to a temp folder. The CLI is called in process (`epc_platform.cli.main.main`) with an injected clock, so the audit log is reproducible.
"""
import io
import json
import tempfile
from pathlib import Path

from disciplines.electrical_lv.store import ProjectStore
from epc_platform.cli.main import main

REPO = Path(__file__).resolve().parents[3]
GOLDEN = REPO / "harness" / "tests" / "golden_projects" / "synthetic_lv_small"
SCHEMAS = REPO / "harness" / "schemas"
CODE = "SYNTH-001"
CLOCK_TEXT = "2026-01-01T00:00:00Z"
RUN_ID = "synth-run-1"
ORCHESTRATOR = ("--actor-role", "orchestrator", "--actor-id", "orc-1")
ENGINEER = ("--actor-role", "engineer_of_record", "--actor-id", "eng-1")


def clock():
    return CLOCK_TEXT


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def epc(root, *argv):
    """(exit code, stdout, stderr) of one in-process `epc` call against the projects root."""
    out, err = io.StringIO(), io.StringIO()
    code = main(["--projects-root", str(root), *argv], stdout=out, stderr=err, clock=clock, env={})
    return code, out.getvalue(), err.getvalue()


def envelope(root, *argv):
    """(exit code, decoded JSON envelope) of one `epc ... --json` call."""
    code, out, err = epc(root, *argv, "--json")
    return code, json.loads(out if out.strip() else err)


def resolved_engine_inputs(work_dir, drawing_date=None):
    """`engine_inputs.json` with the catalog folder turned into an absolute path, written to `work_dir`; returns (file path, the document).
    With `drawing_date` (ISO date) the document also carries `drawings.date`, which pins the dates, times and GUIDs of the drawings (MIG-3Z)."""
    doc = read_json(GOLDEN / "engine_inputs.json")
    if drawing_date:
        doc["drawings"] = {"date": drawing_date}
    doc["datasheets"]["catalog_dir"] = str(GOLDEN / doc["datasheets"]["catalog_dir"])
    path = Path(work_dir) / "engine_inputs.resolved.json"
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return path, doc


class SyntheticRun:
    """A project in its own temp projects root: `init`, the intake inputs, and (`run`) the pipeline, all through the CLI."""

    def __init__(self, run_id=RUN_ID, drawing_date=None):
        self.holder = tempfile.TemporaryDirectory()
        self.base = Path(self.holder.name)
        self.root = self.base / "projects"
        self.root.mkdir()
        self.work = self.base / "work"
        self.work.mkdir()
        self.run_id = run_id
        self.project = self.root / CODE
        self.drawing_date = drawing_date
        self.engine_inputs_file, self.engine_inputs = resolved_engine_inputs(self.work, drawing_date)
        self.init_result = None
        self.run_result = None

    def cleanup(self):
        self.holder.cleanup()

    def init(self):
        """`epc init` with the intake answers, then the project inputs (load list, engine inputs) are added to `inputs/` before the freeze."""
        self.init_result = envelope(self.root, "init", CODE, "--answers", str(GOLDEN / "intake_answers.json"), *ORCHESTRATOR)
        store = ProjectStore(self.project)
        store.write_input("loads/loads.json", (GOLDEN / "loads.json").read_bytes())
        store.write_input("engine_inputs.json", self.frozen_engine_inputs())
        return self.init_result

    def frozen_engine_inputs(self):
        """The bytes of the engine inputs frozen in `inputs/`: the golden file, plus `drawings.date` when the run pins the drawing date."""
        if not self.drawing_date:
            return (GOLDEN / "engine_inputs.json").read_bytes()
        doc = read_json(GOLDEN / "engine_inputs.json")
        doc["drawings"] = {"date": self.drawing_date}
        return (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")

    def run(self, run_id=None, revision="R0"):
        self.run_result = envelope(self.root, "run", CODE, "--loads", str(GOLDEN / "loads.json"), "--engine-inputs", str(self.engine_inputs_file),
                                   "--run-id", run_id or self.run_id, "--revision", revision, "--detail", *ORCHESTRATOR)
        return self.run_result

    def start(self):
        self.init()
        self.run()
        return self

    def ssot(self, name):
        return read_json(self.project / "ssot" / name)

    def stage_files(self):
        return sorted((self.project / "ssot").glob("stage_*.json"))

    def manifests(self):
        return sorted((self.project / "deliverables").glob("*/*.manifest.json"))


def normalise_dxf_hashes(value):
    """A copy of a JSON value in which the SHA-256 and size (and nothing else) of every `.dxf` entry is blanked.

    The DXF writer (ezdxf, `epc_dxf/svg_to_dxf.py`) stamps the current time and random GUIDs into every file, so those hashes differ between two runs.
    """
    if isinstance(value, list):
        return [normalise_dxf_hashes(v) for v in value]
    if not isinstance(value, dict):
        return value
    out = {k: normalise_dxf_hashes(v) for k, v in value.items()}
    names = [out.get(k) for k in ("path", "title", "source")]
    if any(isinstance(n, str) and n.endswith(".dxf") for n in names):
        for key in ("sha256", "output_sha256", "bytes"):
            if key in out:
                out[key] = None
    return out
