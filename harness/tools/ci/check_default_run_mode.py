"""The default mode of a run may be `edit` only on `dev` and on work branches: never on `main` or on a release (ADR-0035).

  python harness/tools/ci/check_default_run_mode.py

`harness/config/default_run_mode` must say `production` or `edit`. It must say `production` on the branch `main`, when `EPC_RELEASE=1` (a release check) or when the pull request
targets `main` (`GITHUB_BASE_REF=main`, the CI of a PR). The promotion from `dev` to `main` sets it with `harness/tools/build/set_default_run_mode.py production`.
"""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import epc_paths as P  # noqa: E402

REPO = P.REPO
FILE = REPO / "harness" / "config" / "default_run_mode"
MODES = ("production", "edit")


def branch():
    """The current branch (empty when it cannot be told, e.g. a detached HEAD)."""
    done = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def strict_needed(current, environ):
    """Why the default must be `production` here, or None when `edit` is allowed."""
    if current == "main":
        return "the branch is main"
    if environ.get("EPC_RELEASE") == "1":
        return "EPC_RELEASE=1 (a release check)"
    if environ.get("GITHUB_BASE_REF") == "main" or environ.get("GITHUB_REF") == "refs/heads/main":
        return "the change goes to main"
    return None


def problems(value, current, environ):
    """The errors of the file for this branch and environment (empty list = fine)."""
    if value not in MODES:
        return [f"{FILE.relative_to(REPO).as_posix()} must say production or edit, it says {value!r}"]
    why = strict_needed(current, environ)
    if value == "edit" and why:
        return [f"the default run mode is `edit` but {why}: run `python harness/tools/build/set_default_run_mode.py production` (ADR-0035)"]
    return []


def main() -> int:
    value = FILE.read_text(encoding="utf-8").strip() if FILE.is_file() else None
    errors = problems(value, branch(), os.environ)
    for e in errors:
        print("ERROR:", e)
    print(f"default run mode: {value} (branch {branch() or '?'})" if not errors else "")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
