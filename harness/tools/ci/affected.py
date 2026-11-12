#!/usr/bin/env python3
"""Which engine suites a change can affect (stdlib only): the basis of the incremental gate.

  python harness/tools/ci/affected.py [BASE]     print the engine areas to test for the files changed since BASE (default: origin/main, else HEAD~1)

An engine is affected when one of its files changed or when it uses (directly or through another engine) an engine that changed. The dependency
edges come from `harness/tools/build/impact_map.py`, which reads them from the code. A change in a shared place (schemas, norm data, tools, platform,
requirements, the gate itself) can affect every engine, so it selects all of them. Documentation-only changes select none.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "build"))
import epc_paths as P  # noqa: E402
import impact_map as IM  # noqa: E402

REPO = P.REPO
SHARED = ("harness/schemas/", "harness/config/normative/", "harness/config/i18n/", "harness/catalogs/", "harness/tools/", "harness/src/platform/",
          "harness/src/disciplines/", "harness/.claude/roster", "requirements", "pyproject", ".github/")
DOC_ONLY_SUFFIXES = (".md", ".txt")


def _git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.splitlines()


def default_base() -> str:
    ok = subprocess.run(["git", "rev-parse", "--verify", "-q", "origin/main"], cwd=REPO, capture_output=True).returncode == 0
    return "origin/main" if ok else "HEAD~1"


def changed_files(base: str) -> list:
    """Files changed since `base` (committed), plus uncommitted and untracked ones."""
    files = set(_git("diff", "--name-only", f"{base}...HEAD")) | set(_git("diff", "--name-only", "HEAD")) | set(_git("ls-files", "--others", "--exclude-standard"))
    return sorted(f.replace("\\", "/") for f in files if f)


def unit_of(rel: str) -> str:
    for unit, root in IM.ENGINE_ROOTS.items():
        engine_dir = P.ENGINE_FOLDERS_REL[unit]
        if rel.startswith(engine_dir + "/"):
            return unit
    return ""


def affected(files: list, all_areas: list) -> list:
    """Engine areas to test for these changed files (a subset of `all_areas`)."""
    if any(f.startswith(SHARED) and not f.endswith(DOC_ONLY_SUFFIXES) for f in files):
        return list(all_areas)
    start = {u for u in (unit_of(f) for f in files) if u}
    edges, _third = IM.scan()
    users = IM.dependents(edges)
    out = set(start)
    for u in start:
        out |= IM.closure(u, users)
    return [a for a in all_areas if a in out]


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    base = argv[0] if argv else default_base()
    print(" ".join(affected(changed_files(base), sorted(IM.ENGINE_PKGS.values()))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
