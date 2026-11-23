#!/usr/bin/env python3
"""Regenerate every generated file in one command (OPT-08), or check that none is stale (COD-15).

  python harness/tools/build/regen_all.py           rewrite: registry, plugins, agents, impact map, engine contracts, norm register report
  python harness/tools/build/regen_all.py --check   fail when any generated file is out of date (use it as a pre-commit check)

Order matters: the registry reads the plugins, so plugins go first.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

# (name, write arguments, check arguments)
STEPS = [
    ("plugins", ["regen_plugins.py"], ["regen_plugins.py", "--check"]),
    ("agents", ["regen_agents.py"], ["regen_agents.py", "--check"]),
    ("impact-map", ["impact_map.py"], ["impact_map.py", "--check"]),
    ("registry", ["epc_build.py", "registry"], ["epc_build.py", "registry", "--check"]),
    ("engine-contracts", ["engine_contracts.py"], ["engine_contracts.py", "--check"]),
    ("norm-register", ["norm_register.py", "--report"], ["norm_register.py", "--report", "--check"]),
]


def run_step(name, args):
    """True when the step's script exits 0; prints its tail when it does not."""
    r = subprocess.run([sys.executable, str(HERE / args[0])] + args[1:], cwd=REPO, capture_output=True, text=True)
    if r.returncode != 0:
        print((r.stdout + r.stderr).strip()[-600:])
    return r.returncode == 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    failed = []
    for name, write, chk in STEPS:
        ok = run_step(name, chk if check else write)
        print(f"{'ok' if ok else 'STALE' if check else 'FAILED':7} {name}")
        failed += [] if ok else [name]
    if not failed:
        return 0
    print(("Out of date: " if check else "Failed: ") + ", ".join(failed) + ("  (run regen_all.py without --check)" if check else ""))
    return 1


if __name__ == "__main__":
    sys.exit(main())
