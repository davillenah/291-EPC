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
from urllib.parse import parse_qs, urlparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath, PureWindowsPath

HARNESS = Path(__file__).resolve().parents[2]
SRC = HARNESS / "src"
PATHS = [str(SRC), str(SRC / "platform")] + [str(p) for p in sorted(SRC.glob("engines/*/*/src"))] + [str(p) for p in sorted(SRC.glob("disciplines/*/src"))]
sys.path[:0] = PATHS
sys.path.insert(0, str(Path(__file__).resolve().parent))
import brief  # noqa: E402
import build  # noqa: E402
import house  # noqa: E402
import pv  # noqa: E402
import runner  # noqa: E402
from disciplines.electrical_lv.intake.form import validate_answers  # noqa: E402
from disciplines.electrical_lv.intake.schema_check import load_schema  # noqa: E402

# Every discipline of the harness (harness/src/disciplines) plus architecture (the `epc_arch` engine). Status as in each README.
DISCIPLINES = ("architectural", "civil", "electrical", "electrical_mv", "pv", "mechanical", "hvac", "piping", "fire", "instrumentation", "telecom")
STATUS = {"electrical": "available", "architectural": "partial", "pv": "available"}      # every other one: planned, no engine or intake yet


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
    """The intake form of the schema; the line voltage is a choice of the two systems the calculation knows (230/400 and 220/380) and has no default."""
    fields = flatten(load_schema("intake_answers.schema.json"))
    for f in fields:
        if f["path"] == "supply.voltage.value":
            f.update(kind="select", options=["400", "380"], required=True, numeric=True)
    return {"id": "electrical", "status": STATUS["electrical"], "fields": fields}


def architectural_form():
    """The description that `epc_arch.author` takes (docstring of the module): floor + rooms as boxes in metres; nothing is assumed."""
    return {"id": "architectural", "status": STATUS["architectural"], "fields": [
        {"path": "floor.name", "kind": "text", "required": True},
        {"path": "floor.index", "kind": "number", "required": True},
        {"path": "floor.wall_thickness_m", "kind": "number", "required": True},
        {"path": "floor.rooms", "kind": "rooms", "required": True,
         "columns": ["code", "name", "west", "south", "east", "north"]},
    ]}


def house_form():
    """The values of a house that the request did not give and the harness proposes (all pending review, see `house_defaults.json`): the page shows them as editable fields."""
    num = lambda p: {"path": p, "kind": "number", "required": False}    # noqa: E731
    return {"id": "house", "status": "available", "fields": [
        num("house.wall_height_m"), num("house.luminaire_power_w"), num("house.luminaire_flux_lm"),
        {"path": "house.receptacles", "kind": "select", "required": False, "options": ["yes", "no"]}, num("house.receptacle_va"), num("house.board_fp"),
        num("house.garden_area_m2"), num("house.garden_lux"), num("house.garden_length_m")]}


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
    makers = {"electrical": electrical_form, "architectural": architectural_form, "pv": pv.form}
    chosen = selected_of(discipline)
    forms = [makers[d]() if d in makers else planned_form(d) for d in chosen]
    if {"electrical", "architectural"} <= set(chosen):
        forms.insert(max(chosen.index("electrical"), chosen.index("architectural")) + 1, house_form())
    return {"discipline": list(chosen), "forms": forms}


def _proposals(said):
    """The form values that are proposals of the harness (not said in the request): the house assumptions, with the receptacles on unless only lighting was asked."""
    d, services = house.DEFAULTS, said["services"]
    return {"house.wall_height_m": d["wall_height_m"], "house.luminaire_power_w": d["luminaire"]["power_w"], "house.luminaire_flux_lm": d["luminaire"]["lamp_flux_lm"],
            "house.receptacles": "no" if services and not services.get("receptacles") else "yes", "house.receptacle_va": d["receptacle"]["power_va"],
            "house.board_fp": d["board"]["fp_default"], "house.garden_lux": d["garden"]["target_lux"], "house.garden_length_m": d["garden"]["length_m"]}


def _floor_values(said, rows, lang):
    """The form values of the proposed floor: its name, the room rows, the type of installation and the garden area (the width of the house times the depth of the garden)."""
    d = house.DEFAULTS
    garden = round(max(r["east"] for r in rows) * d["garden"]["depth_m"], 1) if said["rooms"].get("garden") else ""
    return {"floor.name": "PLANTA BAJA" if lang == "es" else "GROUND FLOOR", "floor.index": 0, "floor.wall_thickness_m": d["wall_thickness_m"],
            "floor.rooms": [{k: r[k] for k in ("code", "name", "west", "south", "east", "north")} for r in rows],
            "site.installation_type": "Vivienda unifamiliar" if lang == "es" else "Single-family house", "house.garden_area_m2": garden}


def interpret(payload):
    """What the request says (`brief.interpret`) and the form values it fills: the rooms of the proposed floor, the services and the proposals of the house.

    {brief, added, values, assumed}: `values` are form paths, `assumed` the paths whose value is a proposal of the harness and not something the request said."""
    lang = payload.get("lang") if payload.get("lang") in ("es", "en") else "es"
    said = brief.interpret(payload.get("request"))
    named = any(k in house.DEFAULTS["rooms"] for k in said["rooms"])
    rows, added = house.propose(said["rooms"], lang, said["floors"]) if named else ([], [])
    values = _floor_values(said, rows, lang) if rows else {}
    values.update(_proposals(said))
    if "pv" in said["disciplines"]:
        values.update(pv.proposals())
    return {"brief": said, "added": added, "values": values, "assumed": [k for k in values if k.startswith(("house.", "pv.")) or k == "floor.wall_thickness_m"]}


def set_path(target, path, value):
    parts = path.split(".")
    for p in parts[:-1]:
        target = target.setdefault(p, {})
    target[parts[-1]] = value


def _value(field, v):
    """One raw form value converted to the type of its field."""
    if (field["kind"] == "number" or field.get("numeric")) and isinstance(v, str):
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


KILLED = {"en": "The run was stopped by the system (signal {sig}), usually for lack of memory; make the plant smaller or free memory and run again.",
          "es": "El sistema detuvo la corrida (señal {sig}), normalmente por falta de memoria; achicá la planta o liberá memoria y corré de nuevo."}


def run_epc(projects_root, args, timeout=120):
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(PATHS), EPC_PROJECTS_ROOT=str(projects_root))
    p = subprocess.run([sys.executable, "-m", "epc_platform.cli", "--json", *args], capture_output=True, text=True, env=env, timeout=timeout)
    try:
        return json.loads(p.stdout)
    except ValueError:
        if p.returncode < 0:      # the process was ended by a signal (the system kills a run that uses all the memory): say so, an empty message tells nothing
            return {"ok": False, "error": {"code": "cli_killed", "message": KILLED["en"].format(sig=-p.returncode) + " / " + KILLED["es"].format(sig=-p.returncode)}}
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
        scratch = HARNESS.parent / "tmp"      # `tmp/` of the repository is git-ignored: simulations live there (owner rule 2026-11-18)
        inside = (resolved == HARNESS.parent or HARNESS.parent in resolved.parents) and scratch not in (resolved, *resolved.parents)
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


def _others(selected):
    """The disciplines without a pipeline of their own: architecture is drawn with the electrical run (`_architecture`) when both are ticked."""
    return [x for x in selected if x != "electrical" and not (x in ("architectural", "pv") and "electrical" in selected)]


def _run_disciplines(selected, root, code, flat, payload, submit):
    """Per-discipline results, the project folder and whether `epc init` created it."""
    results, folder, created = {}, (Path(root) / code) if code else None, False
    if "electrical" in selected:      # electrical first: `epc init` needs a new or empty folder
        results["electrical"], made = _electrical(root, code, flat, submit)
        created, folder = made is not None and results["electrical"]["state"] == "created", made or folder
    for d in _others(selected):
        results[d] = {"state": "saved" if submit else "valid", "note": "no_pipeline"}
        if submit:
            _pending(folder or root, d, payload, flat)
    return results, folder, created


def _architecture(selected, flat, submit):
    """The architecture of a building run: (result, run data or None). It needs the electrical discipline as well; the plans are drawn and read back, nothing is written."""
    if not {"electrical", "architectural"} <= set(selected):
        return None, None
    rows, plans, problem = build.check_floor(flat, flat.get("floor.rooms"))
    if problem:
        return {"state": "invalid", "errors": [], "problem": problem}, None
    loads, inputs = build.engine_inputs(flat, rows, list(plans))
    return {"state": "created" if submit else "valid", "errors": []}, {"plans": plans, "loads": loads, "inputs": inputs}


def _pv(selected, flat, submit):
    """The photovoltaic project: (result, data or None). It needs the electrical discipline (the project is created by `epc init`). On submit PVGIS is asked once for the typical year (before anything is written)."""
    if "pv" not in selected:
        return None, None
    if "electrical" not in selected:
        return {"state": "invalid", "errors": [], "problem": {"code": "pv_needs_electrical", "detail": ""}}, None
    problem = pv.check(flat, building="architectural" in selected)
    if problem:
        return {"state": "invalid", "errors": [], "problem": problem}, None
    if not submit:
        return {"state": "valid", "errors": []}, None
    try:
        weather = pv.fetch_weather(flat)
    except Exception as exc:      # PvError (English and Spanish) or anything the network raises: the project is not created
        return {"state": "invalid", "errors": [], "problem": {"code": "pvgis", "detail": f"{exc} / {getattr(exc, 'es', '')}"[:300]}}, None
    return {"state": "created", "errors": []}, {"section": pv.section(flat), "drawings": pv.drawings_options(pv.values_of(flat)[0]), "files": {pv.WEATHER_FILE: weather}, "aux": None if "architectural" in selected else (pv.aux_loads(flat), pv.board_of(flat)), "feeders": pv.feeders_of(flat)}


def _merge_pv(data, pv_data):
    """The run data with the PV section: a building run keeps its plans and loads; a PV-only run has no plans and an empty load list (the plant generates, it does not consume)."""
    if not pv_data:
        return data
    (areas, loads), board = pv_data["aux"] or (([], []), None)
    data = data or {"plans": {}, "loads": {"schema_version": "1.0", "areas": areas, "loads": loads}, "inputs": {"board": board, "documents": {"formats": ["pdf", "docx", "xlsx"]}, "circuits": {"AUX-01": {"kind": "rcbo"}}, "pv_feeders": pv_data.get("feeders")}}      # the auxiliary service carries its residual-current device (TT needs it, stage 8)
    inputs = dict(data["inputs"], pv=pv_data["section"], **({"drawings": dict(data["inputs"].get("drawings") or {}, **pv_data["drawings"])} if pv_data.get("drawings") else {}))
    return dict(data, inputs=inputs, files=pv_data["files"])


def _launch(root, folder, code, data, created):
    """Writes the plans as intake inputs (before the run freezes them) and starts the run; the job id, or None when the project was not created."""
    if not (data and created):
        return None
    from disciplines.electrical_lv.store import ProjectStore
    store = ProjectStore(folder)
    for name, text in data["plans"].items():
        store.write_input(f"plans/{name}", text)
    for name, text in data.get("files", {}).items():
        store.write_input(name, text)
    return runner.start(run_epc, root, code, data["loads"], data["inputs"])


def _building_and_plant(selected, flat, submit):
    """(architecture result, PV result, run data) of the building and the photovoltaic plant, merged into one run."""
    arch, data = _architecture(selected, flat, submit)
    pv_result, pv_data = _pv(selected, flat, submit)
    return arch, pv_result, _merge_pv(data, pv_data)


def _validated(default_root, payload, submit):
    """The result of the checks that must pass before anything is written, or None when they do; `check` mode never fails here."""
    if not submit:
        return None
    checked = handle(default_root, payload, False)
    return checked if any(x["state"] == "invalid" for x in checked["results"].values()) else None


def handle(default_root, payload, submit):
    selected = selected_of(payload.get("discipline", []))
    root, code, error = _checked_root(payload, default_root)
    if not selected or error:
        return {"results": {}, "error": error or "no_discipline"}
    flat = dict(payload.get("answers", {}))
    if code:
        flat["project_code"] = flat.get("project_code") or code
    refused = _validated(default_root, payload, submit)
    if refused:
        return refused
    arch, pv_result, data = _building_and_plant(selected, flat, submit)
    if (pv_result or {}).get("state") == "invalid":
        return {"results": {"pv": pv_result}}
    results, folder, created = _run_disciplines(selected, root, code, flat, payload, submit)
    results.update({k: v for k, v in (("architectural", arch), ("pv", pv_result)) if v})
    report = {"results": results}
    if submit:
        report["saved_docs"] = save_docs(folder or root, created, payload)
        report["job"] = _launch(root, folder, code, data, created)
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
            url = urlparse(self.path)
            query = {k: v[0] for k, v in parse_qs(url.query).items()}
            if url.path == "/api/job":
                return self._send(200, runner.status(query.get("id", "")))
            if url.path == "/api/file":
                return self._file(query.get("job", ""), query.get("p", ""))
            if self.path.startswith("/api/form"):
                d = self.path.split("discipline=")[-1] if "discipline=" in self.path else "electrical"
                return self._send(200, form_of(d.replace("%2C", ",")))
            self._send(200, index.read_bytes(), "text/html")

        def _file(self, job, rel):
            target = runner.file_of(job, rel)
            if target is None:
                return self._send(404, {"error": "not found"})
            ctype = {".pdf": "application/pdf", ".png": "image/png"}.get(target.suffix.lower(), "application/octet-stream")
            data = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition", f'inline; filename="{target.name}"')
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if self.path == "/api/interpret":
                return self._send(200, interpret(payload))
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
