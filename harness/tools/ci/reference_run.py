#!/usr/bin/env python3
"""One command runs the fictional reference project and compares it with the previous run (GEN-02, OPT-14).

  python harness/tools/ci/reference_run.py [--out tmp/reference] [--name NAME]      (no --name: every reference project, one after the other)

The projects are the invented ones of `harness/tests/golden_projects/` (fictional data only): `synthetic_lv_small` (office floor), `reference_dwelling`
(AEA 90364-7-771 dwelling), `reference_shed` (industrial shed with motors) and `reference_pv_plant` (small photovoltaic plant). Each run happens in a temporary projects root and
is timed per stage (`EPC_TIMINGS`, OPT-01). The report is written to `<out>/<name>/latest.json`; the one it replaces becomes `previous.json`, and the
difference (status of each stage, findings, files, seconds) is printed. `tmp/` is git-ignored: nothing here is ever committed.
Exit code 1 when a stage status, the number of findings or the set of delivered files differs from the previous report (times never fail it).
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HARNESS_TESTS = REPO / "harness" / "tests" / "integration"
PROJECTS = ("synthetic_lv_small", "reference_dwelling", "reference_shed", "reference_pv_plant")


def run_reference(name="synthetic_lv_small"):
    """Run the project once; the report is a plain dict (stage statuses and seconds, findings, delivered files)."""
    os.environ["EPC_TIMINGS"] = "1"
    os.environ.setdefault("EPC_RUN_MODE", "edit")
    sys.path.insert(0, str(HARNESS_TESTS))
    import synthetic_lv as S                                     # the helpers that drive the real `epc` CLI
    run = S.SyntheticRun(drawing_date="2026-03-04", folder=REPO / "harness" / "tests" / "golden_projects" / name)
    started = time.perf_counter()
    try:
        run.init()
        code, answer = run.run()
        seconds = round(time.perf_counter() - started, 2)
        state = run.ssot("../master_project_state.json") if (run.project / ".epc" / "master_project_state.json").exists() else {}
        stages = [{"stage": e.get("number"), "status": e.get("status")} for e in state.get("stages", [])]
        timing_file = next(run.project.rglob("stage_timings.json"), None)
        timings = json.loads(timing_file.read_text(encoding="utf-8"))["stages"] if timing_file else []
        files = sorted(str(p.relative_to(run.project)) for p in (run.project / "deliverables").rglob("*") if p.is_file())
        findings = sum(len(S.read_json(p).get("findings", [])) for p in run.stage_files())
        return {"project": name, "exit_code": code, "seconds": seconds, "stages": stages, "stage_seconds": {t["slug"]: t["seconds"] for t in timings},
                "findings": findings, "files": files}
    finally:
        run.cleanup()


def compare(old, new):
    """The differences that matter (never the times): list of plain sentences."""
    out = []
    if old.get("stages") != new.get("stages"):
        out.append("stage statuses differ")
    if old.get("findings") != new.get("findings"):
        out.append(f"findings {old.get('findings')} -> {new.get('findings')}")
    gone, added = sorted(set(old.get("files", [])) - set(new["files"])), sorted(set(new["files"]) - set(old.get("files", [])))
    out += [f"file no longer delivered: {f}" for f in gone] + [f"new file delivered: {f}" for f in added]
    if old.get("exit_code") != new.get("exit_code"):
        out.append(f"exit code {old.get('exit_code')} -> {new.get('exit_code')}")
    return out


def one(out, name):
    """Run one project, store its report, print the result; 0 when it ran and nothing differs from the previous report (or there is none)."""
    report = run_reference(name)
    folder = Path(out) / name
    folder.mkdir(parents=True, exist_ok=True)
    latest, previous = folder / "latest.json", folder / "previous.json"
    old = json.loads(latest.read_text(encoding="utf-8")) if latest.exists() else None
    if old is not None:
        previous.write_text(json.dumps(old, indent=2) + "\n", encoding="utf-8")
    latest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"{name}: exit {report['exit_code']}, {report['seconds']} s, {len(report['stages'])} stages, {report['findings']} findings, {len(report['files'])} files")
    for slug, sec in report["stage_seconds"].items():
        print(f"  {slug:28} {sec:7.2f} s")
    if report["exit_code"] != 0:
        print("the reference run did not finish")
        return 1
    if old is None:
        print("no previous report: this one is the baseline")
        return 0
    diffs = compare(old, report)
    print("same as the previous run" if not diffs else "differences with the previous run:\n  " + "\n  ".join(diffs))
    return 1 if diffs else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(REPO / "tmp" / "reference"))
    ap.add_argument("--name", choices=PROJECTS, help="one project (default: all of them)")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import run_gate                                              # the gate knows where every engine lives
    sys.path[:0] = [p for p in run_gate.HARNESS_ENV["PYTHONPATH"].split(os.pathsep) if p]
    codes = [one(a.out, name) for name in ([a.name] if a.name else PROJECTS)]
    return 1 if any(codes) else 0


if __name__ == "__main__":
    sys.exit(main())
