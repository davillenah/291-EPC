"""Single source of truth: no two versioned files of the product may hold the same content.

  python harness/tools/ci/check_single_source.py

A datum (a norm value, a criterion, an example, a logo) lives in one file; whatever needs it points to that file or gets a copy *generated* at build time
(see `engine_data` in the plugin manifests). This check fails when two tracked files are byte-identical. Test fixtures are pinned expected outputs and are exempt;
the few intentional pairs are listed below with their reason.
"""
import hashlib
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import epc_paths as P  # noqa: E402

REPO = P.REPO
LOGOS = f"{P.engine_src_rel('titleblock')}/epc_titleblock/assets"
EXEMPT_PARTS = ("/tests/fixtures/", "/node_modules/", "/dist/", "/incoming/")      # incoming/: modules that stand alone carry a copy of the contract and the prompt by design
MIN_BYTES = 200
ALLOWED = [
    ({f"{LOGOS}/client-logo-DAVH.svg", f"{LOGOS}/provider-logo-DAVH.svg",
      f"{LOGOS}/client-logo-DAVH.png", f"{LOGOS}/provider-logo-DAVH.png", "assets/logo.png"},
     "sample logos: the generator reads one file per role (client / provider) and the sample uses the platform's own artwork for both"),
    ({f"{P.PLUGINS_REL}/aea-calc/LICENSE", f"{P.PLUGINS_REL}/iram-titleblock/LICENSE"}, "each plugin carries its own license text"),
]


def tracked() -> list:
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout.splitlines()
    return [f for f in out if not any(p in "/" + f for p in EXEMPT_PARTS)]


def main() -> int:
    groups = defaultdict(list)
    for f in tracked():
        p = REPO / f
        if p.is_file() and p.stat().st_size >= MIN_BYTES:
            groups[hashlib.sha256(p.read_bytes()).hexdigest()].append(f)
    allowed = [a[0] for a in ALLOWED]
    bad = [sorted(v) for v in groups.values() if len(v) > 1 and not any(set(v) <= a for a in allowed)]
    for v in bad:
        print("DUPLICATE (same content):", *v, sep="\n  ")
    print("single source:", "OK" if not bad else f"{len(bad)} duplicated file group(s): keep one and point the others to it")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
