"""Read-only view of the norm records of the engines a run called, with their review state (for the deliverable manifest, MIG-32).

The norm register is derived from the engines (`harness/tools/build/norm_register.py`, which a discipline may not import):
hand records live in `<engine package>/norm_register/*.json`; the rules of the AEA and lighting engines are indexed from their own
fields; the review state is read from the `data/review.json` of the AEA engine (the register tool reads the same file).
This module mirrors that tool's ids and review points (a test compares both) and NEVER writes or changes a review state.

Review status of a record as the manifest lists it:
  verified        the register record says `verified`, or `review.json` says `approved` for its review point
  rejected        the register record says `rejected`
  pending review  anything else (also when the engine ships no review data)

Limitation: the stage outputs do not name the exact records a value came from, so ALL records of the called engine packages are
returned (a superset), and engines used only inside another engine (for example the drawing engine's own helpers) are not listed.
"""
import importlib
import importlib.util
import json
import re
from pathlib import Path

VERIFIED, PENDING, REJECTED = "verified", "pending review", "rejected"
REVIEW_PACKAGE = "epc_aea90364"
# package -> (rule files glob, key that holds the rules, register id prefix, rule id prefix kind)
RULE_SOURCES = {"epc_aea90364": ("reglas", "aea90364"), "epc_lighting": ("rules", "lighting")}


def _load(path):
    return json.loads(Path(path).read_bytes().decode("utf-8-sig"))


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def package_dir(package):
    """Folder of an installed engine package, or None when it cannot be found (nothing is imported)."""
    spec = importlib.util.find_spec(package)
    return Path(spec.origin).parent if spec and spec.origin else None


def read_review_points(package=REVIEW_PACKAGE):
    """{review point: status} from the engine's `data/review.json`; empty when there is none."""
    folder = package_dir(package)
    path = folder / "data" / "review.json" if folder else None
    if not path or not path.is_file():
        return {}
    return {k: v.get("status") for k, v in (_load(path).get("points") or {}).items() if isinstance(v, dict)}


def _status(register_status, review):
    if register_status == "rejected":
        return REJECTED
    if register_status == "verified" or review == "approved":
        return VERIFIED
    return PENDING


def _hand_records(folder, points):
    out = []
    for path in sorted((folder / "norm_register").glob("*.json")) if (folder / "norm_register").is_dir() else []:
        for rec in _load(path).get("records", []):
            out.append({"id": rec["id"], "review_status": _status(rec.get("status"), points.get(rec.get("review_point")))})
    return out


def _rule_point(package, data, rule):
    """Review point and id of one rule, the way the register tool derives them."""
    key, short = RULE_SOURCES[package]
    if package == "epc_aea90364":
        src = rule.get("fuente", {})
        point = f"rule:{_slug(str(src.get('norma', '?')) + ' ' + str(src.get('edicion', '')))}|{rule['id']}"
    else:
        point = f"lighting-rule:{_slug(data.get('norm'))}|{rule['id']}"
    return point, f"{short}.rule.{_slug(rule['id'])}"


def _rules_folder(package, folder):
    """Folder with the rule files of an engine: the AEA rules are norm data in the normative folder (MIG-37a, through the engine's loader); the others live in the package."""
    if package == REVIEW_PACKAGE:
        try:
            return importlib.import_module(package + ".norm_data").rules_dir()
        except (ImportError, FileNotFoundError):
            return folder / "rules"
    return folder / "rules"


def _rule_records(package, folder, points):
    rules = _rules_folder(package, folder)
    if package not in RULE_SOURCES or not rules.is_dir():
        return []
    out = []
    for path in sorted(rules.glob("*.json")):
        if path.name.startswith("_"):
            continue
        data = _load(path)
        for rule in data.get(RULE_SOURCES[package][0], []):
            point, rid = _rule_point(package, data, rule)
            out.append({"id": rid, "review_status": _status(None, points.get(point))})
    return out


def read_norm_records(packages):
    """Norm records (id, review_status) of the given engine packages, unique by id and sorted by id. Read only."""
    points = read_review_points()
    found = {}
    for package in sorted(set(packages)):
        folder = package_dir(package)
        if folder is None:
            continue
        for rec in _hand_records(folder, points) + _rule_records(package, folder, points):
            found[rec["id"]] = rec
    return [found[k] for k in sorted(found)]
