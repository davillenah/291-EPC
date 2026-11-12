"""Output of the `epc` commands. `--json` prints the api envelope as canonical JSON (sorted keys); the default is short English text.

Rendering only lays out what the api returned: no value is computed or invented here.
"""
import json

NONE = "-"


def as_json(envelope):
    """The envelope as canonical JSON text (sorted keys, two-space indent, no ASCII escaping)."""
    return json.dumps(envelope, sort_keys=True, indent=2, ensure_ascii=False, default=str)


def table(headers, rows):
    """A plain text table: header, rule, rows; every column as wide as its longest cell."""
    cells = [[str(h) for h in headers]] + [[NONE if v is None else str(v) for v in row] for row in rows]
    widths = [max(len(r[i]) for r in cells) for i in range(len(headers))]
    lines = ["  ".join(c.ljust(w) for c, w in zip(row, widths)).rstrip() for row in cells]
    lines.insert(1, "  ".join("-" * w for w in widths))
    return "\n".join(lines)


def pairs(items):
    width = max((len(k) for k, _ in items), default=0)
    return "\n".join(f"{k.ljust(width)}  {NONE if v is None else v}" for k, v in items)


def _stages(data):
    rows = [(s["number"], s["slug"], s["title"], s["engines"], s["status"], "yes" if s["wired"] else "no") for s in data["stages"]]
    return table(("#", "stage", "title", "engines", "status", "wired"), rows) + f"\n{data['count']} stages"


def _engines_list(data):
    rows = [(e["package"], e["group"], e["area"], e["version"]) for e in data["engines"]]
    return table(("package", "group", "area", "version"), rows) + f"\n{data['count']} engines"


def _engines_info(data):
    return pairs([("package", data["package"]), ("group", data["group"]), ("area", data["area"]), ("version", data["version"]),
                  ("path", data["path"]), ("norm register", "yes" if data["has_norm_register"] else "no"),
                  ("public modules", ", ".join(data["public_modules"]))])


def _norms(data):
    counts = ", ".join(f"{n} {s}" for s, n in data["by_status"].items()) or "none"
    rows = [(r["id"], r["review_status"]) for r in data["records"]]
    return table(("record", "review status"), rows) + f"\n{data['count']} records ({counts}) in {len(data['packages'])} package(s)"


def _norms_pending(data):
    head = f"{data['pending_points']} pending point(s) in {data['units_with_pending']} of {data['units']} unit(s)"
    rows = [(r["name"], r["total"], r["pending"]) for r in data.get("rows", [])]
    return head if not rows else table(("unit", "points", "pending"), rows) + f"\n{head}"


def _status(data):
    audit, workflow = data["audit"], data["workflow"]
    events = table(("seq", "time", "actor", "action", "result"),
                   [(e["seq"], e["ts"], f"{e['actor']['role']}/{e['actor']['id']}", e["action"], e["result"]) for e in audit["last"]])
    head = pairs([("project", data["project"]), ("workflow", workflow["state"]), ("next", ", ".join(workflow["allowed_transitions"]) or None),
                  ("transitions", workflow["transitions_done"]), ("reviews", len(data["reviews"])),
                  ("audit events", f"{audit['count']} (chain {'intact' if audit['chain_intact'] else 'BROKEN'})")])
    return f"{head}\n\nLast events\n{events}"


def _run(data):
    run = data["run"]
    rows = [(r["stage"], r["status"], r["message"]) for r in run["results"]]
    tail = f"run {data['pipeline_run_id']}: {run['summary']['stages_run']} stage(s) run, workflow {data['workflow_state']}"
    return table(("stage", "status", "message"), rows) + "\n" + tail


def _init(data):
    return f"project {data['project']} created at {data['path']} (workflow {data['workflow_state']})"


def _review(data):
    return f"{data['corrections']} correction(s) recorded in {data['review_file']} (workflow {data['workflow_state']})"


def _transition(data):
    return f"workflow {data['workflow_state']}"


RENDERERS = {"init": _init, "run": _run, "status": _status, "review": _review, "approve": _transition, "issue": _transition,
             "engines list": _engines_list, "engines info": _engines_info, "norms": _norms, "norms-pending": _norms_pending, "stages": _stages}


def render(key, data):
    return RENDERERS[key](data)


def error_text(envelope):
    error = envelope["error"]
    return f"error [{error['code']}]: {error['message']}"
