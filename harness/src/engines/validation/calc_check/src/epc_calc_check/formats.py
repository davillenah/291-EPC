"""Group C, format (format-check): the run and its stage outputs have the shape the pipeline promises. Reads data only; no engine call."""
import math
import re

from epc_calc_check import view as V
from epc_calc_check._values import is_number, is_sha256, walk
from epc_calc_check.findings import SEVERITIES, VERIFIERS, issue

FINDING_KEYS = ("id", "run_id", "verifier", "severity", "document", "field", "value", "expected", "clause", "action", "evidence")
FINDING_ID = re.compile(r"F-[0-9]{4}")
MAX_PER_RULE = 25      # a broken run must not bury the reader: the first cases of a kind are reported


def _structure(view):
    out, last = [], 0
    if not isinstance(view.run.get("results"), list):
        return [issue("CC-F01", "model", "results", type(view.run.get("results")).__name__, "a list of stage results", "Pass the JSON form of the pipeline result.", "run_result")]
    for res in view.listed:
        number, status = res.get("stage"), res.get("status")
        if number not in V.STAGE_SLUGS or isinstance(number, bool):
            out.append(issue("CC-F01", "model", "results/stage", number, "a stage number 1..16", "Fix the stage number.", "run_result"))
        elif number <= last:
            out.append(issue("CC-F01", "model", f"results/{number}/stage", number, f"greater than {last}", "Stages are unique and in ascending order.", "run_result"))
        elif res.get("slug") not in (None, V.STAGE_SLUGS[number]):
            out.append(issue("CC-F01", "model", f"results/{number}/slug", res.get("slug"), V.STAGE_SLUGS[number], "Fix the stage name.", "run_result"))
        last = number if isinstance(number, int) and number > last else last
        if status not in V.STATUSES:
            out.append(issue("CC-F01", "model", f"results/{number}/status", status, list(V.STATUSES), "Fix the stage status.", "run_result"))
    return out


def _required(view):
    out = []
    for number, keys in V.REQUIRED_OUTPUTS.items():
        res = view.results.get(number)
        if not res or res.get("status") != "ok":
            continue
        got = res.get("outputs") if isinstance(res.get("outputs"), dict) else {}
        out += [issue("CC-F02", view.slug(number), f"outputs/{k}", None, "present", "Re-run the stage.", f"stage {number} outputs") for k in keys if k not in got]
    for number, keys in V.ROW_FIELDS.items():
        for row in view.rows(number):
            out += [issue("CC-F02", view.slug(number), f"circuits/{row.get('circuit', '?')}/{k}", None, "present", "Re-run the stage.", f"stage {number} row")
                    for k in keys if k not in row]
    return out


def _finite(view):
    out = []
    for res in view.listed:
        for path, leaf in walk({"outputs": res.get("outputs"), "findings": res.get("findings")}):
            if isinstance(leaf, float) and not math.isfinite(leaf):
                out.append(issue("CC-F03", V.STAGE_SLUGS.get(res.get("stage"), "model"), path, leaf, "a finite number", "Find the stage that produced it; re-run.", f"stage {res.get('stage')}"))
    return out[:MAX_PER_RULE]


def _row_types(number, row, tag):
    out = []
    for key in V.NUMERIC_FIELDS.get(number, ()):
        if key in row and not is_number(row[key]) and not (row[key] is None and key in V.NULLABLE_FIELDS) and not (isinstance(row[key], float) and not math.isfinite(row[key])):
            out.append((key, row[key], "a number"))
    for key in V.FLAG_FIELDS.get(number, ()):
        if key in row and row[key] is not None and not isinstance(row[key], bool):
            out.append((key, row[key], "true or false"))
    return [(tag, *o) for o in out]


def _types(view):
    out = []
    for number in V.CIRCUIT_STAGES:
        for row in view.rows(number):
            out += [issue("CC-F04", view.slug(number), f"circuits/{tag}/{key}", found, expected, "Fix the stage output.", f"stage {number} row")
                    for tag, key, found, expected in _row_types(number, row, row.get("circuit", "?"))]
    return out


def _duplicates(view):
    out = []
    for number in V.CIRCUIT_STAGES:
        for key in ("circuit", "load_id"):
            values = [r.get(key) for r in view.rows(number) if r.get(key) is not None]
            out += [issue("CC-F05", view.slug(number), f"circuits/{v}/{key}", v, "unique", "Each circuit and load appears once.", f"stage {number} rows")
                    for v in dict.fromkeys(x for x in values if values.count(x) > 1)]
    return out


def hash_locations(view, numbers):
    """(stage, path, value) of every hash the stages in `numbers` carry."""
    for number in numbers:
        out = view.outputs(number)
        if number == 1:
            yield number, "outputs/inputs_manifest/manifest_sha256", (out.get("inputs_manifest") or {}).get("manifest_sha256")
            for i, f in enumerate((out.get("inputs_manifest") or {}).get("files") or []):
                yield number, f"outputs/inputs_manifest/files/{i}/sha256", f.get("sha256") if isinstance(f, dict) else None
        if number == 3 and "manifest_sha256" in out:
            yield number, "outputs/manifest_sha256", out["manifest_sha256"]
        for i, f in enumerate(out.get("files") or [] if number == 14 else []):
            yield number, f"outputs/files/{i}/sha256", f.get("sha256") if isinstance(f, dict) else None
        for i, d in enumerate(out.get("documents") or [] if number == 15 else []):
            yield number, f"outputs/documents/{i}/sha256", d.get("sha256") if isinstance(d, dict) else None


def hash_issues(view, numbers):
    return [issue("CC-F06", view.slug(n), path, value, "64 lowercase hexadecimal characters", "Recompute the hash from the file or document.", f"stage {n}")
            for n, path, value in hash_locations(view, numbers) if not is_sha256(value)]


def _hashes(view):
    return hash_issues(view, (1, 3))


def _units(view):
    out = []
    for number in range(1, 13):
        out += _unit_issues(view, number, view.outputs(number), "outputs")
    return out[:MAX_PER_RULE]


def _unit_issues(view, number, node, path):
    out = []
    if isinstance(node, dict):
        if "unit" in node and (not isinstance(node["unit"], str) or not node["unit"].strip() or ("value" in node and not is_number(node["value"]))):
            out.append(issue("CC-F07", view.slug(number), path, node, "a value with a unit", "Give the value and its unit.", f"stage {number}"))
        for k, v in node.items():
            out += _unit_issues(view, number, v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out += _unit_issues(view, number, v, f"{path}/{i}")
    return out


def _finding_errors(view, number, f, i):
    out, where = [], f"findings/{i}"
    if not isinstance(f, dict):
        return [issue("CC-F08", view.slug(number), where, f, "a finding object", "Fix the finding.", f"stage {number}")]
    missing = [k for k in FINDING_KEYS if k not in f]
    if missing:
        out.append(issue("CC-F08", view.slug(number), where, missing, "all finding keys", "Fix the finding.", f"stage {number}"))
    for key, allowed in (("severity", SEVERITIES), ("verifier", VERIFIERS + ("input-verifier", "standards-reviewer", "final-auditor"))):
        if key in f and f[key] not in allowed:
            out.append(issue("CC-F08", view.slug(number), f"{where}/{key}", f[key], list(allowed), "Fix the finding.", f"stage {number}"))
    if "id" in f and not (isinstance(f["id"], str) and FINDING_ID.fullmatch(f["id"])):
        out.append(issue("CC-F08", view.slug(number), f"{where}/id", f["id"], "F-0001 style id", "Fix the finding.", f"stage {number}"))
    return out


def _repeated(ids):
    return list(dict.fromkeys(i for i in ids if i is not None and ids.count(i) > 1))


def _findings(view):
    """Finding schema per finding, and unique ids: inside each stage while the run is going (every stage numbers from F-0001), across the whole run once renumbered."""
    out, run_ids = [], []
    for res in view.listed:
        stage_ids = []
        for i, f in enumerate(res.get("findings") if isinstance(res.get("findings"), list) else []):
            out += _finding_errors(view, res.get("stage"), f, i)
            stage_ids.append(f.get("id") if isinstance(f, dict) else None)
        if not view.renumbered:
            out += [issue("CC-F08", view.slug(res.get("stage")), "findings/id", x, "unique ids in the stage", "Renumber the findings of the stage.", f"stage {res.get('stage')}")
                    for x in _repeated(stage_ids)]
        run_ids += stage_ids
    if view.renumbered:
        out += [issue("CC-F08", "model", "findings/id", x, "unique ids in the run", "Renumber the findings of the run.", "run_result") for x in _repeated(run_ids)]
    return out


def _same_circuits(view):
    """Every circuit stage lists the same circuits; stage 5 (demand) lists loads only, so it may omit feeders but not add circuits."""
    sets = {n: [r.get("circuit") for r in view.rows(n)] for n in V.CIRCUIT_STAGES if view.rows(n)}
    full = {n: t for n, t in sets.items() if n != 5}
    union = set().union(*map(set, sets.values())) if sets else set()
    out = [issue("CC-F09", view.slug(n), f"circuits/{t}", None, "listed in every circuit stage", "Re-run the stages from the same circuit list.", f"stage {n}")
           for n, tags in full.items() for t in sorted(union - set(tags), key=str)]
    extra = set(sets.get(5, [])) - set().union(*map(set, full.values())) if full else set()
    return out + [issue("CC-F09", view.slug(5), f"circuits/{t}", t, "a circuit of the other stages", "Re-run the stages from the same circuit list.", "stage 5") for t in sorted(extra, key=str)]


CHECKS = (_structure, _required, _finite, _types, _duplicates, _hashes, _units, _findings, _same_circuits)


def check_format(view):
    for check in CHECKS:
        yield from check(view)
