"""Runs the pipeline of a project in the background and reports it: progress by stage and the deliverables by numbered folder.

`start(...)` launches `epc run` through the CLI (the designed interface) in a thread; `status(id)` reads what the pipeline itself records in the project folder
(`.epc/epc_progress.txt`, one line per finished stage) and, when it ends, lists `deliverables/TR-NNN/<NN_FOLDER>/<file>`. The page never sees JSON or paths of the inputs.
"""
import json
import os
import re
import secrets
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

JOBS = {}
STAGES = 12
LOCK = threading.Lock()


def new_run_id():
    return f"run-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{secrets.token_hex(4)}"


def _write(doc):
    fd, name = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)
    return name


def start(run_epc, root, code, loads, inputs):
    """Launches the run; returns the job id. `run_epc(root, args)` is the CLI call of the server (so tests can replace it)."""
    job = secrets.token_hex(6)
    folder, rid = Path(root) / code, new_run_id()
    JOBS[job] = {"state": "running", "folder": folder, "run_id": rid, "error": None, "mode": None}
    args = ["--projects-root", str(root), "run", code, "--loads", _write(loads), "--engine-inputs", _write(inputs), "--run-id", rid]

    def work():
        res = run_epc(root, args, timeout=900)
        with LOCK:
            ok = bool(res.get("ok")) and bool(res.get("data", {}).get("run", {}).get("summary", {}).get("ok"))
            JOBS[job].update(state="done" if ok else "failed", error=None if ok else _why(res), mode=(res.get("data") or {}).get("mode"))
    threading.Thread(target=work, daemon=True).start()
    return job


def _why(res):
    """A short text of why a run did not finish: the CLI error, or the first blocked or failed stage."""
    if not res.get("ok"):
        return (res.get("error") or {}).get("message", "")[:400]
    for r in res["data"]["run"]["results"]:
        if r["status"] in ("blocked", "failed"):
            return f"stage {r['stage']}: {r['message']}"[:400]
    return ""


def progress(folder, rid):
    """[{stage, status, message}] of the stages the run has finished, from the progress log of the project."""
    log = Path(folder) / ".epc" / "epc_progress.txt"
    try:
        lines = log.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        parts = [p.strip() for p in line.split("|", 4)]
        m = re.match(r"run (\S+)", parts[1]) if len(parts) == 5 else None
        s = re.match(r"stage (\d+)", parts[2]) if m else None
        if s and m.group(1) == rid:
            out.append({"stage": int(s.group(1)), "status": parts[3], "message": "" if parts[4] == "-" else parts[4]})
    return out


def _files(folder, where):
    return [{"name": f.name, "size": f.stat().st_size, "path": f.relative_to(folder).as_posix()} for f in sorted(where) if f.is_file()]


def deliverables(folder):
    """{transmittal, folders: [{name, files: [{name, size, path}]}]} of the latest transmittal, folders in their numbered order; `path` is relative to the project folder."""
    base = Path(folder) / "deliverables"
    trs = sorted(p for p in base.glob("TR-*") if p.is_dir()) if base.is_dir() else []
    if not trs:
        return {"transmittal": None, "folders": []}
    tr = trs[-1]
    folders = [{"name": d.name, "files": _files(folder, d.rglob("*"))} for d in sorted(p for p in tr.iterdir() if p.is_dir())]
    loose = _files(folder, tr.iterdir())
    return {"transmittal": tr.name, "folders": ([{"name": tr.name, "files": loose}] if loose else []) + folders}


def status(job):
    """The state of a job: running | done | failed, the stages finished so far, and (when it ended) the deliverables."""
    info = JOBS.get(job)
    if not info:
        return {"state": "unknown"}
    with LOCK:
        state, error = info["state"], info["error"]
    out = {"state": state, "stages": progress(info["folder"], info["run_id"]), "total": STAGES, "path": str(info["folder"]), "error": error, "mode": info["mode"]}
    if state != "running":
        out["deliverables"] = deliverables(info["folder"])
    return out


def file_of(job, rel):
    """(absolute path) of a deliverable of the job when `rel` is inside its `deliverables/` folder, else None."""
    info = JOBS.get(job)
    if not info:
        return None
    base = (Path(info["folder"]) / "deliverables").resolve()
    target = (Path(info["folder"]) / rel).resolve()
    return target if base in target.parents and target.is_file() else None
