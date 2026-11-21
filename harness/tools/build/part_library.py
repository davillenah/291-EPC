"""Writes the 3D part library: every equipment record of the PV data (inverters, accessories, module formats and technologies, mounting structures) drawn from its description (`epc_drawing.part_library`).

  python harness/tools/build/part_library.py [--out DIR] [--date YYYY-MM-DD]      DIR defaults to `tmp/part_library/` of the repository (git-ignored)

It writes `PV_part_library.dxf` and `PV_part_library_freecad.FCMacro` and prints how many parts were drawn and which records give too little to draw (their elements are listed by id).
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "harness" / "src" / "engines" / "calculation" / "pv" / "src" / "epc_pv" / "data"
FOLDERS = ("pv_inverters/inverters", "pv_inverters/accessories", "pv_modules/formats", "pv_modules/technologies", "mounting_structures/ground", "mounting_structures/roof")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(REPO / "tmp" / "part_library"))
    ap.add_argument("--date", default=None)
    args = ap.parse_args(argv)
    sys.path[:0] = [str(REPO / "harness" / "src" / "engines" / "cad" / "drawing" / "src"), str(REPO / "harness" / "src" / "platform")] + [str(p) for p in (REPO / "harness" / "src" / "engines").glob("*/*/src")]
    from epc_drawing import part_library
    records = [json.loads(p.read_text(encoding="utf-8")) for f in FOLDERS for p in sorted((DATA / f).glob("*.json"))]
    done = part_library.write(records, args.out, "PV", args.date)
    print(f"{done['parts']} parts of {len(records)} records -> {done['dxf']}, {done['freecad']}")
    for rid, ids in sorted(done["skipped"].items()):
        print(f"  {rid}: gives too little to draw: {', '.join(ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
