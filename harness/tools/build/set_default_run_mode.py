"""Set the default mode of a run: the promotion step from `dev` to `main` (ADR-0035).

  python harness/tools/build/set_default_run_mode.py production    # before a release: what `main` must say
  python harness/tools/build/set_default_run_mode.py edit          # on `dev`, after a release branch was merged back or to start working in edit mode

It writes `harness/config/default_run_mode` and nothing else; committing it is the caller's act. After it, `python harness/tools/ci/check_default_run_mode.py` (with `EPC_RELEASE=1` for a release) says
whether the file is right for the branch.
"""
import sys
from pathlib import Path

FILE = Path(__file__).resolve().parents[2] / "config" / "default_run_mode"
MODES = ("production", "edit")


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1 or args[0] not in MODES:
        print(f"usage: set_default_run_mode.py {'|'.join(MODES)}", file=sys.stderr)
        return 2
    FILE.write_text(args[0] + "\n", encoding="utf-8", newline="\n")
    print(f"{FILE}: {args[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
