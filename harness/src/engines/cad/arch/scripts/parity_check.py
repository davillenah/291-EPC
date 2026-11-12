"""Reads the same truth plan from each format (SVG, DXF, PNG) and compares what the engine finds with what the plan really has: counts, and (`geometry`) by place with `geometric_metrics`.

    python scripts/parity_check.py [p1 p2 ...] [--root out/planta_prueba] [--report out/parity_report.json]

Counts only (no matching by position yet): f1 of an element kind is 2*min(found, truth) / (found + truth). `cross_format_delta` is the largest difference of a count between formats."""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from epc_arch import ArchError, Options, recognize     # noqa: E402
import geometric_metrics                                # noqa: E402

FORMATS = ("svg", "dxf", "png")
KINDS = (("doors", "door", "puertas"), ("windows", "window", "ventanas"), ("openings", "opening", "huecos"))


def f1(found: int, truth: int) -> float:
    return 1.0 if found == truth == 0 else 2.0 * min(found, truth) / (found + truth)


def measure(path: Path, truth: dict) -> dict:
    t0 = time.time()
    try:
        r = recognize(path.read_bytes(), path.name, Options(background=False))
    except ArchError as e:
        return {"error": str(e)}
    d = r.as_dict()
    c = d["counts"]
    out = {"seconds": round(time.time() - t0, 1), "walls": c["walls"], "rooms": len(d["rooms"]), "scale_known": bool(d["units_per_metre"]),
           "wall_thickness_cm": None if not d["wall_thickness"] or not d["units_per_metre"] else round(100 * d["wall_thickness"] / d["units_per_metre"], 1)}
    for key, _, tkey in KINDS:
        out[key] = c[key]
        out[key[:-1] + "_f1" if key != "openings" else "opening_f1"] = round(f1(c[key], len(truth[tkey])), 2)
    out["room_count_delta"] = out["rooms"] - len(truth["ambientes"])
    out["geometry"] = geometric_metrics.measure(r.architecture, truth)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plans", nargs="*")
    ap.add_argument("--root", default=str(HERE.parent / "out" / "planta_prueba"))
    ap.add_argument("--report", default=str(HERE.parent / "out" / "parity_report.json"))
    a = ap.parse_args(argv)
    root = Path(a.root)
    report = {}
    for pid in a.plans or sorted(p.name for p in root.iterdir() if p.is_dir()):
        truth = json.loads((root / pid / "verdad.json").read_text(encoding="utf-8"))
        res = {f: measure(root / pid / f"planta.{f}", truth) for f in FORMATS if (root / pid / f"planta.{f}").exists()}
        ok = [r for r in res.values() if "error" not in r]
        delta = max((max(r[k] for r in ok) - min(r[k] for r in ok) for k in ("walls", "doors", "windows", "openings", "rooms")), default=0)
        report[pid] = {"truth": {"doors": len(truth["puertas"]), "windows": len(truth["ventanas"]), "openings": len(truth["huecos"]), "rooms": len(truth["ambientes"]),
                                 "thickness_cm": sorted({m["espesor_cm"] for m in truth["muros"]})}, "formats": res, "cross_format_delta": delta}
        print(pid, json.dumps({f: {k: v for k, v in r.items() if k in ("doors", "windows", "openings", "rooms", "walls", "error")} for f, r in res.items()}), "truth", report[pid]["truth"]["doors"], report[pid]["truth"]["windows"], report[pid]["truth"]["openings"], report[pid]["truth"]["rooms"], "delta", delta)
    Path(a.report).write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
