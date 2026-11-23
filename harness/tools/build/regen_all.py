#!/usr/bin/env python3
"""Regenerate every generated file in one command (OPT-08), or check that none is stale (COD-15).

  python harness/tools/build/regen_all.py           rewrite: registry, plugins, agents, impact map, norm register report
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
    ("norm-register", ["norm_register.py", "--report"], ["norm_register.py", "--report", "--check"]),
]


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    check = "--check" in argv
    failed = []
    for name, write, chk in STEPS:
        cmd = [sys.executable, str(HERE / (chk if check else write)[0])] + (chk if check else write)[1:]
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        status = "ok" if r.returncode == 0 else "STALE" if check else "FAILED"
        print(f"{status:7} {name}")
        if r.returncode != 0:
            failed.append(name)
            print((r.stdout + r.stderr).strip()[-600:])
    if failed:
        print(("Out of date: " if check else "Failed: ") + ", ".join(failed) + ("  (run regen_all.py without --check)" if check else ""))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
