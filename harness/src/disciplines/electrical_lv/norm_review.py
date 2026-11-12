"""Read-only view of the norm review units: which norm points exist and how many are still pending (MIG-38b).

This is the part of the old norms page (the parked web backend, `norms.service.units`) that the harness needs: the same units, the same points
and the same status rule, read straight from the engines' data files and from their `review.json`. It NEVER writes a file or changes a review state.

A unit is a group of points the owner reviews together: the rules of one standard and edition, the AEA calculation tables, the typical values of
the plan, receptacles and HVAC engines, the design-criteria catalog and the rules of each lighting norm. A point is `pending` until `review.json`
says `approved`, `stale` when it was approved but the value changed since (fingerprint mismatch), `rejected` when rejected.
"""
import hashlib
import json
import re
from pathlib import Path

STATUSES = ("approved", "rejected", "pending", "stale")
TABLE_SECTIONS = {"cap": "tablas_capacidad", "fac": "factores_correccion", "const": "constantes"}
TYPICAL_SECTIONS = {
    "plan": ("table:plan-valores-tipicos", "Cables, canalizaciones y diseño automático · valores típicos (a confirmar)", ("sizing", "occupancy", "design"), True),
    "receptacles": ("table:receptacles-valores-tipicos", "Tomacorrientes · valores típicos (a confirmar)", ("uses", "mounting", "circuits"), True),
    "hvac": ("table:hvac-valores-tipicos", "Climatización · valores típicos (a confirmar)", ("params", "solar", "ventilation"), False),
}


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def fingerprint(value):
    """Digest of the canonical JSON of a value (the one the review stores when it approves a point)."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sources():
    """The data files of the engines, resolved through the engines' own loaders (imported lazily)."""
    from epc_aea90364 import aea_rules, aea_tables, norm_data
    from epc_hvac import config as hvac_config
    from epc_lighting import norm_data as lighting_norms
    from epc_plan import core as plan_core
    from epc_receptacles import config as receptacles_config
    return {"plan": Path(plan_core.TYPICAL), "receptacles": Path(receptacles_config.USES), "hvac": Path(hvac_config.TYPICAL), "rules": Path(aea_rules.CARPETA),
            "tables": Path(aea_tables.RUTA_JSON), "criteria": norm_data.criteria_file("electrical"), "review": Path(norm_data.REVIEW),
            "lighting": Path(lighting_norms.RULES_DIR)}


def review_points(path):
    """{point id: review record} from `review.json`; empty when the file does not exist."""
    path = Path(path)
    return read_json(path).get("points", {}) if path.is_file() else {}


def status_of(record, value):
    if not record:
        return "pending"
    if record["status"] == "approved" and record.get("sha") != fingerprint(value):
        return "stale"
    return record["status"]


def rule_units(folder):
    """One unit per standard and edition: {unit id: (name, [(key, value)])}."""
    units = {}
    for path in sorted(p for p in Path(folder).glob("*.json") if not p.name.startswith("_")):
        for rule in read_json(path).get("reglas", []):
            src = rule.get("fuente", {})
            uid = "rule:" + slug(f"{src.get('norma', '?')} {src.get('edicion', '')}")
            name = f"{src.get('norma', '?')} ({src.get('edicion', '')})"
            units.setdefault(uid, (name, []))[1].append((rule["id"], rule))
    return units


def table_points(path):
    data = read_json(path)
    return [(f"{short}:{tid}", value) for short, section in TABLE_SECTIONS.items() for tid, value in data.get(section, {}).items()]


def typical_points(path, sections, skip_note):
    """(key, value) of a typical-values file, section by section; a missing file gives no points."""
    if not path or not Path(path).is_file():
        return []
    data = read_json(path)
    return [(f"{section}:{k}", v) for section in sections for k, v in data.get(section, {}).items() if not (skip_note and k == "note")]


def lighting_units(folder):
    """One unit per lighting norm; the engine's own `review` flag is not part of the reviewed value."""
    units = {}
    for path in sorted(Path(folder).glob("*.rules.json")):
        data = read_json(path)
        points = [(r["id"], {k: v for k, v in r.items() if k != "review"}) for r in data["rules"]]
        units["lighting-rule:" + slug(data["norm"])] = (f"{data['norm']} · iluminación (valores por revisar)", points)
    return units


def all_units(src=None):
    """{unit id: (kind, name, [(key, value)])} in the order of the old norms page: lighting, rules, tables, typical values, criteria."""
    src = src or sources()
    out = {uid: ("lighting_rule", name, pts) for uid, (name, pts) in lighting_units(src["lighting"]).items()}
    out.update({uid: ("rule", name, pts) for uid, (name, pts) in sorted(rule_units(src["rules"]).items())})
    out["table:aea-calculo"] = ("table", "Tablas y constantes de cálculo (AEA 90364-7-771, 2006)", table_points(src["tables"]))
    for key, (uid, name, sections, skip_note) in TYPICAL_SECTIONS.items():
        points = typical_points(src[key], sections, skip_note)
        if points:
            out[uid] = ("table", name, points)
    catalog = read_json(src["criteria"])["criteria"]
    out["criterion:ar-electrical"] = ("criterion", "Criterios de diseño · valores base (AR, eléctrica)", [(c["id"], c) for c in catalog])
    return out


def units(src=None):
    """[{id, kind, name, counts}] with counts {total, approved, rejected, pending, stale}. Read only."""
    src = src or sources()
    review = review_points(src["review"])
    out = []
    for uid, (kind, name, points) in all_units(src).items():
        counts = {"total": len(points), "approved": 0, "rejected": 0, "pending": 0, "stale": 0}
        for key, value in points:
            counts[status_of(review.get(f"{uid}|{key}"), value)] += 1
        out.append({"id": uid, "kind": kind, "name": name, "counts": counts})
    return out


def summary(src=None):
    """Totals over every unit: units, units with pending points, pending points (pending + stale), and the unit rows."""
    rows = [{"id": u["id"], "name": u["name"], "total": u["counts"]["total"], "pending": u["counts"]["pending"] + u["counts"]["stale"]} for u in units(src)]
    return {"units": len(rows), "units_with_pending": sum(1 for r in rows if r["pending"]), "pending_points": sum(r["pending"] for r in rows), "rows": rows}
