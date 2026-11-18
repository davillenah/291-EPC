"""Local landing page of the harness: one screen with a request box, the guided form and the discipline picker.

`python harness/tools/landing/server.py [--port 8291] [--projects-root DIR]` serves `index.html` and three calls:
  GET  /api/form?discipline=electrical,architectural,civil (any subset)  the form, built from the schemas (never typed by hand)
  POST /api/check   {discipline, answers}                          validates with the harness validator, nothing is written
  POST /api/submit  {discipline, request, answers}                 electrical: runs `epc init` (CLI); the others have no intake yet and say so

Only the standard library. Projects go OUTSIDE the repository (`--projects-root` or EPC_PROJECTS_ROOT; default `~/epc-landing-projects`).
The user sees no JSON: the page renders fields and messages; the files below are internal.
"""
import argparse
import base64
import re
import json
import os
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath, PureWindowsPath

HARNESS = Path(__file__).resolve().parents[2]
SRC = HARNESS / "src"
PATHS = [str(SRC), str(SRC / "platform")] + [str(p) for p in sorted(SRC.glob("engines/*/*/src"))] + [str(p) for p in sorted(SRC.glob("disciplines/*/src"))]
sys.path[:0] = PATHS
from disciplines.electrical_lv.intake.form import validate_answers  # noqa: E402
from disciplines.electrical_lv.intake.schema_check import load_schema  # noqa: E402

# Every discipline of the harness (harness/src/disciplines) plus architecture (the `epc_arch` engine). Status as in each README.
DISCIPLINES = ("architectural", "civil", "electrical", "electrical_mv", "mechanical", "hvac", "piping", "fire", "instrumentation", "telecom")
STATUS = {"electrical": "available", "architectural": "partial"}      # every other one: planned, no engine or intake yet


def _scalar(path, spec, required):
    kind = spec.get("type")
    field = {"path": path, "required": required}
    if "enum" in spec:
        field.update(kind="select", options=spec["enum"])
    elif kind == "number":
        field["kind"] = "number"
    else:
        field["kind"] = "text"
    return field


def flatten(schema, prefix="", required_parent=True):
    """Fields of a JSON schema object, nested objects flattened to dotted paths (`supply.voltage.value`)."""
    required = set(schema.get("required", []))
    out = []
    for name, spec in schema.get("properties", {}).items():
        path = f"{prefix}{name}"
        if spec.get("type") == "object":
            out += flatten(spec, path + ".", name in required)
        elif spec.get("type") == "array":
            out.append({"path": path, "kind": "list", "required": False})
        elif path == "supply.voltage.unit" or path == "supply.short_circuit_level.unit":
            out.append({"path": path, "kind": "unit", "value": spec["enum"][0], "required": True})
        else:
            f = _scalar(path, spec, name in required)
            out.append(f)
    return out


def electrical_form():
    return {"id": "electrical", "status": STATUS["electrical"], "fields": flatten(load_schema("intake_answers.schema.json"))}


def architectural_form():
    """The description that `epc_arch.author` takes (docstring of the module): floor + rooms as boxes in metres; nothing is assumed."""
    return {"id": "architectural", "status": STATUS["architectural"], "fields": [
        {"path": "floor.name", "kind": "text", "required": True},
        {"path": "floor.index", "kind": "number", "required": True},
        {"path": "floor.wall_thickness_m", "kind": "number", "required": True},
        {"path": "floor.rooms", "kind": "rooms", "required": True,
         "columns": ["code", "name", "west", "south", "east", "north"]},
    ]}


def planned_form(discipline):
    """Disciplines without an intake schema yet: only what the engineer wants and under which standard (saved as a request, nothing is calculated)."""
    return {"id": discipline, "status": "planned", "fields": [
        {"path": f"{discipline}.scope", "kind": "text", "required": True},
        {"path": f"{discipline}.standard", "kind": "text", "required": False},
    ]}


def selected_of(discipline):
    """`electrical,civil` (or a list, or `all`) -> the known disciplines in canonical order; never empty."""
    asked = discipline if isinstance(discipline, (list, tuple)) else str(discipline).split(",")
    chosen = DISCIPLINES if "all" in asked else tuple(d for d in DISCIPLINES if d in asked)
    return chosen


def form_of(discipline):
    makers = {"electrical": electrical_form, "architectural": architectural_form}
    chosen = selected_of(discipline)
    return {"discipline": list(chosen), "forms": [makers[d]() if d in makers else planned_form(d) for d in chosen]}


def set_path(target, path, value):
    parts = path.split(".")
    for p in parts[:-1]:
        target = target.setdefault(p, {})
    target[parts[-1]] = value


def _value(field, v):
    """One raw form value converted to the type of its field."""
    if field["kind"] == "number" and isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return v
    if field["kind"] == "list" and isinstance(v, str):
        return [x.strip() for x in v.split(",") if x.strip()]
    return v


def clean(flat, form):
    """Dotted flat answers -> nested answers; empty values dropped, numbers converted, units fixed by the schema."""
    nested = {}
    for f in form["fields"]:
        if f["kind"] == "unit":
            if flat.get(f["path"].rsplit(".", 1)[0] + ".value") not in (None, ""):
                set_path(nested, f["path"], f["value"])
            continue
        v = flat.get(f["path"])
        if v not in (None, "", []):
            set_path(nested, f["path"], _value(f, v))
    return nested


def run_epc(projects_root, args):
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(PATHS), EPC_PROJECTS_ROOT=str(projects_root))
    p = subprocess.run([sys.executable, "-m", "epc_platform.cli", "--json", *args], capture_output=True, text=True, env=env, timeout=120)
    try:
        return json.loads(p.stdout)
    except ValueError:
        return {"ok": False, "error": {"code": "cli", "message": (p.stderr or p.stdout)[-400:]}}


def split_folder(text):
    """`E:\\00_X\\ES-FORD-CDM` or a POSIX path -> (parent folder, project code). The last folder is the project code."""
    text = (text or "").strip().rstrip("\\/")
    if not text:
        return None, None
    pure = PureWindowsPath(text) if re.match(r"^[A-Za-z]:[\\/]", text) or "\\" in text else PurePosixPath(text)
    return Path(str(pure.parent)), pure.name


def _checked_root(payload, default_root):
    """(root, project code, error): the folder the person typed split in parent and code; refused inside the repository."""
    root, code = split_folder(payload.get("folder"))
    if root is None:
        return default_root, None, None
    try:
        resolved = Path(root).resolve()
        inside = resolved == HARNESS.parent or HARNESS.parent in resolved.parents
    except OSError:
        inside = False
    return root, code, ("inside_repo" if inside else None)


def _electrical(root, code, flat, submit):
    """Validate the electrical answers; on submit run `epc init`. Returns (result, folder or None)."""
    answers = clean(flat, form_of("electrical")["forms"][0])
    answers.setdefault("language", flat.get("language") or "es")
    errors = validate_answers(answers)
    if code and answers.get("project_code") != code:
        errors.append(f"project_code: must equal the folder name {code}")
    if errors or not submit:
        return {"state": "invalid" if errors else "valid", "errors": errors}, None
    res = run_epc(root, ["--projects-root", str(root), "init", answers["project_code"], "--answers", _tmp(answers)])
    return {"state": "created" if res.get("ok") else "failed", "detail": res}, Path(root) / answers["project_code"]


def _pending(where, d, payload, flat):
    """A discipline without a pipeline: its request is saved, nothing is calculated."""
    answers = clean(flat, form_of(d)["forms"][0])
    pending = where / "_pending"
    pending.mkdir(parents=True, exist_ok=True)
    (pending / f"{d}_request.json").write_text(json.dumps({"request": payload.get("request", ""), "answers": answers}, indent=1), encoding="utf-8")


def _run_disciplines(selected, root, code, flat, payload, submit):
    """Per-discipline results, the project folder and whether `epc init` created it."""
    results, folder, created = {}, (Path(root) / code) if code else None, False
    for d in sorted(selected, key=lambda x: x != "electrical"):   # electrical first: `epc init` needs a new or empty folder
        if d == "electrical":
            results[d], made = _electrical(root, code, flat, submit)
            created, folder = made is not None and results[d]["state"] == "created", made or folder
            continue
        results[d] = {"state": "saved" if submit else "valid", "note": "no_pipeline"}
        if submit:
            _pending(folder or root, d, payload, flat)
    return results, folder, created


def handle(default_root, payload, submit):
    selected = selected_of(payload.get("discipline", []))
    root, code, error = _checked_root(payload, default_root)
    if not selected or error:
        return {"results": {}, "error": error or "no_discipline"}
    flat = dict(payload.get("answers", {}))
    if code:
        flat["project_code"] = flat.get("project_code") or code
    results, folder, created = _run_disciplines(selected, root, code, flat, payload, submit)
    report = {"results": results}
    if submit:
        report["saved_docs"] = save_docs(folder or root, created, payload)
    return report


def save_docs(folder, created, payload):
    """The request text and the attached documents: as intake inputs when `epc init` made the project, otherwise in `_pending/`."""
    docs = payload.get("docs", [])
    text = payload.get("request", "")
    names = []
    if created:
        from disciplines.electrical_lv.store import ProjectStore
        store = ProjectStore(folder)
        if text:
            store.write_input("minutes/request.md", text)
        for d in docs:
            name = Path(d["name"]).name
            store.write_input(f"docs/{name}", base64.b64decode(d["data"]))
            names.append(name)
    else:
        base = folder / "_pending"
        (base / "docs").mkdir(parents=True, exist_ok=True)
        if text:
            (base / "request.md").write_text(text, encoding="utf-8")
        for d in docs:
            name = Path(d["name"]).name
            (base / "docs" / name).write_bytes(base64.b64decode(d["data"]))
            names.append(name)
    return names


def _tmp(answers):
    fd, name = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(answers, fh)
    return name


def make_handler(root):
    index = Path(__file__).parent / "index.html"

    class H(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path.startswith("/api/form"):
                d = self.path.split("discipline=")[-1] if "discipline=" in self.path else "electrical"
                return self._send(200, form_of(d.replace("%2C", ",")))
            self._send(200, index.read_bytes(), "text/html")

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if self.path == "/api/check":
                return self._send(200, handle(root, payload, False))
            if self.path == "/api/submit":
                return self._send(200, handle(root, payload, True))
            self._send(404, {"error": "not found"})

        def log_message(self, *a):
            pass

    return H


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8291)
    ap.add_argument("--projects-root", default=os.environ.get("EPC_PROJECTS_ROOT") or str(Path.home() / "epc-landing-projects"))
    a = ap.parse_args(argv)
    root = Path(a.projects_root).resolve()
    if HARNESS.parent in root.parents or root == HARNESS.parent:
        sys.exit("the projects root must be outside the repository")
    root.mkdir(parents=True, exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(root))
    print(f"landing on http://127.0.0.1:{a.port}  projects: {root}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
