#!/usr/bin/env python3
"""Coverage floor over the Python code, measured while the gate runs the suites.

  python harness/tools/ci/check_coverage.py            # combine the data the gate collected and compare each area with harness/tools/ci/coverage_floor.json
  python harness/tools/ci/check_coverage.py --update   # write the floor from the data now collected (floor = measured percentage, rounded down to 0.1, minus TOLERANCE)

The suites run under `coverage run --parallel-mode` with COVERAGE_FILE pointing at `.cov/.coverage`; this script combines the pieces and groups the files by area.
Code that runs in a child process (the engine's generators called by the backend) is not measured: the golden tests of the engine cover it.
Open-source: coverage (Apache-2.0).
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import epc_paths as P  # noqa: E402

REPO = P.REPO
COV_DIR = REPO / ".cov"
FLOOR = REPO / "harness" / "tools" / "ci" / "coverage_floor.json"
TOLERANCE = 0.3                      # points: runs are not byte-identical (threads, timing)
AREAS = {                            # area -> path fragment of its production code
    **{f"engine-{n}": f"/{P.engine_src_rel(n)}/" for n in (
        "aea90364", "calc_common", "load_balance", "voltage_drop", "feeder_sizing", "short_circuit", "grounding", "selectivity", "transformer_sizing", "rules", "standards", "calc_check", "dxf", "symbols", "titleblock", "plan", "arch", "lighting", "receptacles", "hvac", "pv", "sld", "mld", "drawing", "documents", "terminal_blocks", "design_basis", "descriptive_report", "boq", "datasheets", "rfq", "cutlist", "walls", "dims")},
}


def combine() -> dict:
    env = dict(os.environ, COVERAGE_FILE=str(COV_DIR / ".coverage"))
    py = sys.executable
    pieces = list(COV_DIR.glob(".coverage.*"))
    if not pieces and not (COV_DIR / ".coverage").is_file():
        print("no coverage data collected: run the gate, which runs the suites under coverage")
        return {}
    if pieces:                                                   # the pieces of this run; a repeated call finds them already combined
        subprocess.run([py, "-m", "coverage", "combine", "--append", "--quiet"], cwd=REPO, env=env, check=True)
    out = COV_DIR / "coverage.json"
    subprocess.run([py, "-m", "coverage", "json", "-q", "-o", str(out)], cwd=REPO, env=env, check=True)
    files = json.loads(out.read_text(encoding="utf-8"))["files"]
    totals = {a: [0, 0] for a in AREAS}                      # statements, covered
    for path, info in files.items():
        norm = "/" + path.replace("\\", "/").lstrip("/")
        for area, frag in AREAS.items():
            if frag in norm:
                s = info["summary"]
                totals[area][0] += s["num_statements"]
                totals[area][1] += s["covered_lines"]
    return {a: {"statements": n, "covered": c, "percent": round(100.0 * c / n, 2) if n else 0.0} for a, (n, c) in totals.items()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--areas", help="comma-separated areas to check (incremental gate: only the suites that ran); default: all")
    a = ap.parse_args(argv)
    if a.areas is not None and not a.areas.strip() and not a.update:     # incremental gate with no engine suite affected: no suite ran, so no area to check
        print("no engine suite ran (incremental gate): no coverage area to check")
        return 0
    now = combine()
    if not now:
        return 1
    if a.update:
        floor = {k: round(max(0.0, int(v["percent"] * 10) / 10 - TOLERANCE), 1) for k, v in now.items()}
        FLOOR.write_text(json.dumps(floor, indent=1) + "\n", encoding="utf-8")
        (P.DOCS / "refactor").mkdir(parents=True, exist_ok=True)
        (P.DOCS / "refactor" / "coverage_baseline.json").write_text(json.dumps(now, indent=1) + "\n", encoding="utf-8")
        print("floor written:", floor)
        return 0
    return 1 if below_floor(now, set(a.areas.split(",")) if a.areas else None) else 0


def below_floor(now: dict, only=None) -> list:
    """Print each area against its floor and return the ones below it (`only`: just these areas, for the incremental gate)."""
    floor = json.loads(FLOOR.read_text(encoding="utf-8")) if FLOOR.is_file() else {}
    bad = []
    for area, v in now.items():
        if only is not None and area not in only:
            continue
        want = floor.get(area, 0.0)
        mark = "FAIL" if v["percent"] < want else "ok  "
        print(f"{mark} {area:18s} {v['percent']:6.2f} %  ({v['covered']}/{v['statements']} statements)  floor {want}")
        if v["percent"] < want:
            bad.append(area)
    return bad


if __name__ == "__main__":
    sys.exit(main())
