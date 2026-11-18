#!/usr/bin/env python3
"""Quality gate: the test battery that must be green before a branch is merged into dev.

  python harness/tools/ci/run_gate.py

Checks
  registry          plugin registry (plugins, skills, agents, engine areas)
  skill-conflicts   duplicate / orphan skills (production rules)
  single-source     no two versioned files hold the same content (one source of truth per datum)
  default-run-mode  the default mode of a run is `production` on main and on a release, `production` or `edit` elsewhere (ADR-0035)
  dev-credentials   no development credential (the MASTER account) is versioned: it can never reach main
  coverage          each area keeps at least its measured coverage (harness/tools/ci/coverage_floor.json); the suites run under `coverage`
  complexity        no function becomes more complex than its baseline; a new function stays at or below 10 (harness/tools/ci/complexity_baseline.json)
  engine-aea90364   AEA 90364 norm engine tests (calculation, rules, data)
  engine-calc_common, engine-load_balance, engine-voltage_drop, engine-feeder_sizing, engine-short_circuit, engine-grounding, engine-selectivity, engine-transformer_sizing, engine-terminal_blocks, engine-design_basis, engine-descriptive_report, engine-boq, engine-datasheets, engine-rfq
                    the calculation modules split out of epc_aea90364 (MIG-37b): shim identity, behaviour and the unit tests that moved with them
  engine-rules      rules engine tests
  engine-standards  standards ingestion and promotion tests
  engine-calc_check  calc_check tests (recalculation, invariants, format and cross-document checks)
  engine-lighting   lighting engine tests (luminaire count, layout, point illuminance)
  engine-receptacles  receptacles engine tests (socket outlets per room, layout, mounting height)
  engine-hvac       HVAC engine tests (cooling load, supply air, ventilation)
  engine-pv         photovoltaic engine tests (sun, plane-of-array irradiance, DC and AC power, strings, pvlib parity)
  engine-drawing    symbol library tests
  engine-documents  document verifiers, CCPM, exporters (environment-dependent tests are skipped)
  intake            customer-input pipeline tests
  agents            the five product agent files equal what the roster and the bodies generate (regen_agents.py --check)
  harness-tests     tests under harness/tests (architecture, unit) with harness/src and every engine on PYTHONPATH
  sld-smoke         single-line diagram generated from the example through the engine, no warnings
  marketplace       plugins assembled in Claude Code's layout, validated with `claude plugin validate --strict`
The engine packages are put on PYTHONPATH, so no installation is needed. Exit code 0 only when every check passes.
"""
import argparse
import concurrent.futures
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import epc_paths as P  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import affected  # noqa: E402

REPO = P.REPO


def first(*paths):
    for p in paths:
        if p and Path(p).exists():
            return Path(p)
    return None


PYTHON = first(REPO / ".venv" / "Scripts" / "python.exe", REPO / ".venv" / "bin" / "python") or Path(sys.executable)
PLUGINS = P.PLUGINS
ENGINE = P.ENGINES
AREAS = ("aea90364", "calc_common", "load_balance", "voltage_drop", "feeder_sizing", "short_circuit", "grounding", "selectivity", "transformer_sizing", "rules", "standards", "calc_check", "dxf", "symbols", "titleblock", "plan", "arch", "lighting", "receptacles", "hvac", "pv", "sld", "mld", "drawing", "documents", "terminal_blocks", "design_basis", "descriptive_report", "boq", "datasheets", "rfq")
BUILD = first(REPO / "harness" / "tools" / "build" / "epc_build.py")
CONFLICTS = first(REPO / "harness" / "tools" / "ci" / "check_skill_conflicts.py")
RESULTS = []
LOCK = threading.Lock()
COV_DIR = REPO / ".cov"
ENGINE_ENV = {"PYTHONPATH": os.pathsep.join([str(P.engine_src(a)) for a in AREAS if P.engine_src(a).is_dir()] + [os.environ.get("PYTHONPATH", "")])}

HARNESS_ENV = {"PYTHONPATH": os.pathsep.join([str(REPO / "harness" / "src"), str(REPO / "harness" / "src" / "platform"), str(REPO / "harness" / "src" / "platform" / "mcp" / "src"), ENGINE_ENV["PYTHONPATH"]])}


def covered(py, source):
    """Prefix that runs a Python module under coverage (data pieces go to .cov/ and are combined by check_coverage.py)."""
    return [py, "-m", "coverage", "run", "--parallel-mode", f"--source={source}", "-m"]


def cov_env(env=None):
    return dict(env or {}, COVERAGE_FILE=str(COV_DIR / ".coverage"))


def keep_failure(name, ok, out):
    """The summary shows three lines of a failed check; its whole output is kept in .cov/ for diagnosis."""
    if not ok:
        COV_DIR.mkdir(exist_ok=True)
        (COV_DIR / f"failed-{name}.txt").write_text(out, encoding="utf-8")


def run(name, cmd, cwd, must_not_contain=None, env=None):
    t0 = time.time()
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, env=dict(os.environ, **(env or {})))
    out = (p.stdout or "") + (p.stderr or "")
    ok = p.returncode == 0 and not (must_not_contain and must_not_contain in out)
    with LOCK:
        RESULTS.append((name, ok, round(time.time() - t0, 1), out.strip().splitlines()[-3:] if not ok else []))
        keep_failure(name, ok, out)
    return ok


def select_areas(changed):
    """All engine areas, or (incremental gate, `--changed [BASE]`) only those a change since BASE can affect."""
    if changed is None:
        return list(AREAS)
    areas = affected.affected(affected.changed_files(changed or affected.default_base()), list(AREAS))
    print(f"incremental gate: {len(areas)} of {len(AREAS)} engine suites ({', '.join(areas) or 'none'})")
    return areas


def suite_jobs(py, areas):
    """(name, command, cwd, options) of every test suite: the engine suites, the intake tests and the harness tests."""
    jobs = []
    for area in areas:
        d = P.engine_dir(area)
        if (d / "tests").is_dir():
            jobs.append((f"engine-{area}", covered(py, str(d / "src")) + ["unittest", "discover", "-s", "tests"], d, {"env": cov_env(ENGINE_ENV)}))
    intake = PLUGINS / "intake-analysis" / "scripts"
    if intake.is_dir():
        jobs.append(("intake", [py, "-m", "unittest", "test_intake"], intake, {}))
    jobs.append(("harness-tests", [py, "-m", "pytest", "harness/tests", "-q", "-p", "no:cacheprovider"], REPO, {"env": HARNESS_ENV}))
    jobs.sort(key=lambda j: j[0] != "harness-tests")                       # the longest first, so the workers stay busy
    return jobs


def run_jobs(jobs, workers):
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for future in [pool.submit(run, name, cmd, cwd, **kw) for name, cmd, cwd, kw in jobs]:
            future.result()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--changed", nargs="?", const="", metavar="BASE",
                    help="incremental: run only the engine suites a change since BASE can affect (default BASE: origin/main, else HEAD~1); the other checks always run")
    ap.add_argument("--jobs", type=int, default=4, help="suites run at the same time (1 = one after the other)")
    a = ap.parse_args()
    py = str(PYTHON)
    shutil.rmtree(COV_DIR, ignore_errors=True)
    COV_DIR.mkdir(exist_ok=True)

    run("registry", [py, str(BUILD), "registry", "--check"], REPO)
    run("skill-conflicts", [py, str(CONFLICTS), "--env", "production"], REPO)
    run("ignored-sources", [py, str(REPO / "harness" / "tools" / "ci" / "check_ignored_sources.py")], REPO)
    run("single-source", [py, str(REPO / "harness" / "tools" / "ci" / "check_single_source.py")], REPO)
    run("dev-credentials", [py, str(REPO / "harness" / "tools" / "ci" / "check_dev_credentials.py")], REPO)
    run("complexity", [py, str(REPO / "harness" / "tools" / "ci" / "check_complexity.py")], REPO)
    run("default-run-mode", [py, str(REPO / "harness" / "tools" / "ci" / "check_default_run_mode.py")], REPO)
    areas = select_areas(a.changed)
    run_jobs(suite_jobs(py, areas), a.jobs)
    run("coverage", [py, str(REPO / "harness" / "tools" / "ci" / "check_coverage.py"), "--areas", ",".join(f"engine-{x}" for x in areas)], REPO)

    run("impact-map", [py, str(REPO / "harness" / "tools" / "build" / "impact_map.py"), "--check"], REPO)
    run("agents", [py, str(REPO / "harness" / "tools" / "build" / "regen_agents.py"), "--check"], REPO)
    run("plugins-generated", [py, str(REPO / "harness" / "tools" / "build" / "regen_plugins.py"), "--check"], REPO)

    example = P.engine_dir("sld") / "examples" / "sld"
    if example.is_dir():
        out = Path(tempfile.mkdtemp(prefix="gate_sld_"))
        run("sld-smoke", [py, "-m", "epc_drawing.board_design", "--xlsx", str(example / "input_for_sld_V1.xlsx"), "--out", str(out), "--name", "SLD_V1"],
            REPO, must_not_contain="AVISO", env=ENGINE_ENV)

    claude = shutil.which("claude")
    if claude and BUILD:
        market = REPO / "dist" / "marketplace"
        if run("marketplace-build", [py, str(BUILD), "marketplace"], REPO) and market.exists():
            targets = [market] + sorted(p for p in (market / "plugins").iterdir() if p.is_dir())
            bad, t0 = [], time.time()
            for tgt in targets:
                p = subprocess.run([claude, "plugin", "validate", "--strict", str(tgt)], capture_output=True, text=True)
                if p.returncode != 0 or "Validation passed" not in (p.stdout or ""):
                    bad.append(tgt.name + ": " + ((p.stdout or "") + (p.stderr or "")).strip().splitlines()[-1][:120])
            RESULTS.append(("claude-validate", not bad, round(time.time() - t0, 1), bad[:3]))
    else:
        print("note: claude CLI not found, skipping official plugin validation")

    width = max(len(r[0]) for r in RESULTS)
    for name, ok, secs, tail in RESULTS:
        print(f"{'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {secs:>5}s")
        for line in tail:
            print("      |", line)
    failed = [r[0] for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed" + (f"  FAILED: {', '.join(failed)}" if failed else "  GATE GREEN"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
