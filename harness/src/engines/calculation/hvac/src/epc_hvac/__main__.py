"""CLI: python -m epc_hvac INPUT.json --out DIR  (writes DIR/hvac_loads.json; exit 0 ok, 1 with `ERROR ...` on stderr)."""
import argparse
import json
import sys
from pathlib import Path

from epc_hvac import HvacError, run


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="epc_hvac", description="Cooling load of the spaces of a JSON document.")
    ap.add_argument("input")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    try:
        result = run(Path(a.input).read_bytes())
    except (HvacError, OSError) as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 1
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "hvac_loads.json").write_text(json.dumps(result.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
