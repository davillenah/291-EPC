#!/usr/bin/env python3
"""PRO-13: harness metrics read from the projects on disk: how many projects and runs, failures per stage, time per stage.

  python harness/tools/ci/harness_metrics.py [--root tmp/projects] [--json]

Nothing is stored or sent: it only reads each project's `.epc/master_project_state.json` (stage statuses) and the `stage_timings.json` of its runs
(written when a run starts with `EPC_TIMINGS=1`, OPT-01). Output goes to the terminal; it is a maintainer tool, not a deliverable.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


NOT_FAILURES = ("ok", "skipped", "not_available")   # a stage with no engine in this phase reports `not_available`: that is not a failure


def _json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def collect(root) -> dict:
    """Metrics of every project under `root` (a folder of projects, each with a hidden `.epc/`)."""
    stages = defaultdict(lambda: {"slug": "", "runs": 0, "failed": 0, "seconds": []})
    projects = runs = timed_runs = 0
    for epc in sorted(Path(root).glob("*/.epc")):
        projects += 1
        for entry in (_json(epc / "master_project_state.json") or {}).get("stages", []):
            row = stages[entry.get("number")]
            row["slug"] = entry.get("slug", row["slug"])
            row["runs"] += 1
            row["failed"] += entry.get("status") not in NOT_FAILURES
        for run_dir in sorted((epc / "runs").glob("*")) if (epc / "runs").is_dir() else []:
            runs += 1
            timing = _json(run_dir / "stage_timings.json")
            if timing:
                timed_runs += 1
                for entry in timing.get("stages", []):
                    stages[entry.get("stage")]["slug"] = entry.get("slug", "")
                    stages[entry.get("stage")]["seconds"].append(entry.get("seconds", 0.0))
    rows = []
    for number in sorted(k for k in stages if k is not None):
        row = stages[number]
        secs = row["seconds"]
        rows.append({"stage": number, "slug": row["slug"], "projects_seen": row["runs"], "failed": row["failed"],
                     "mean_seconds": round(sum(secs) / len(secs), 3) if secs else None, "max_seconds": max(secs) if secs else None})
    return {"projects": projects, "runs": runs, "runs_with_timings": timed_runs, "stages": rows}


def render(metrics) -> str:
    lines = [f"projects: {metrics['projects']}  runs: {metrics['runs']}  runs with timings: {metrics['runs_with_timings']}", "",
             f"{'stage':<5} {'name':<24} {'seen':>5} {'failed':>6} {'mean s':>8} {'max s':>8}"]
    for r in metrics["stages"]:
        mean = "-" if r["mean_seconds"] is None else f"{r['mean_seconds']:.3f}"
        top = "-" if r["max_seconds"] is None else f"{r['max_seconds']:.3f}"
        lines.append(f"{r['stage']:<5} {r['slug']:<24} {r['projects_seen']:>5} {r['failed']:>6} {mean:>8} {top:>8}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default="tmp/projects", help="folder that holds the projects")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not Path(args.root).is_dir():
        print(f"no such folder: {args.root}", file=sys.stderr)
        return 2
    metrics = collect(args.root)
    print(json.dumps(metrics, indent=2) if args.json else render(metrics))
    return 0


if __name__ == "__main__":
    sys.exit(main())
