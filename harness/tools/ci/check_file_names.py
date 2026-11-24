"""File-name convention guard (one separator style, one case).

  python harness/tools/ci/check_file_names.py            # check
  python harness/tools/ci/check_file_names.py --update   # rewrite the legacy list (only to shrink it)

Rules for every tracked file (see harness/docs/NAMING.md):
  1. Code and data files (.py .json .jsonl .toml .yml .yaml .ps1 .txt .xlsx .dxf .svg .png) are lower snake_case: `a_b.c`, no `-`, no capitals.
  2. A folder never mixes `-` and `_` in the names of its files (an `X_Y` next to an `X-Y`).
Fixed names (README.md, CHANGELOG.md, CLAUDE.md, ADR-NNNN-*, dot files) and generated or third-party trees are exempt.
Files that already broke a rule are listed in `file_names_legacy.json`; the list can only shrink: a new file must comply.
"""
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2].parent
LEGACY = Path(__file__).with_name("file_names_legacy.json")
CODE_DATA = {".py", ".json", ".jsonl", ".toml", ".yml", ".yaml", ".ps1", ".txt", ".xlsx", ".dxf", ".svg", ".png"}
SNAKE = re.compile(r"_{0,2}[a-z0-9]+(_[a-z0-9]+)*_{0,2}(\.[a-z0-9]+)*")
EXEMPT_PREFIX = ("harness/docs/validation/", ".github/")
EXEMPT_PARTS = ("/golden", "/library/", "/fixtures/", "/reference_cases/", "/samples/")     # coded symbol names (291_E_LV_SLD_...), fixtures and third-party samples
EXEMPT_NAMES = {"requirements-dev.txt", "requirements.txt", "CMakeLists.txt"}


def tracked():
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout
    return [p for p in out.splitlines() if p and not p.startswith(EXEMPT_PREFIX) and not any(x in p for x in EXEMPT_PARTS)]


def stem_of(name):
    return name[: name.rfind(".")] if "." in name else name


def offenders(files):
    bad = set()
    seen = defaultdict(lambda: [set(), set()])
    for p in files:
        folder, _, name = p.rpartition("/")
        suffix = Path(name).suffix
        if name.startswith(".") or name in EXEMPT_NAMES or name.startswith("ADR-"):
            continue
        if suffix in CODE_DATA and not SNAKE.fullmatch(name.removesuffix(suffix)) and not name.endswith(".schema.json"):
            bad.add(p)
        if suffix in CODE_DATA or suffix == ".md":
            s = stem_of(name)
            seen[folder][0].add(p) if "-" in s else None
            seen[folder][1].add(p) if "_" in s else None
    for dashed, under in seen.values():
        if dashed and under:
            bad |= dashed | under
    return bad


def main():
    update = "--update" in sys.argv
    files = tracked()
    bad = offenders(files) | {p for p in files if p.endswith(".schema.json") and not SNAKE.fullmatch(p.rpartition("/")[2][: -len(".schema.json")])}
    legacy = set(json.loads(LEGACY.read_text())) if LEGACY.exists() else set()
    if update:
        LEGACY.write_text(json.dumps(sorted(bad & (legacy or bad)), indent=1) + "\n")
        print(f"file-names: legacy list holds {len(bad & (legacy or bad))} file(s)")
        return 0
    new = sorted(bad - legacy)
    gone = sorted(legacy - bad)
    for p in new:
        print("FAIL name breaks the convention (lower snake_case, one separator per folder):", p)
    for p in gone:
        print("FAIL fixed or removed, delete it from file_names_legacy.json (run --update):", p)
    print("file-names:", "OK" if not (new or gone) else f"{len(new)} new offender(s), {len(gone)} stale legacy entr(ies)")
    return 1 if new or gone else 0


if __name__ == "__main__":
    sys.exit(main())
