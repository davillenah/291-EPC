"""CLI: python -m epc_pv INPUT.json --out DIR  (writes DIR/pv_yield.json; exit 0 ok, 1 with `ERROR ...` on stderr in English and Spanish)."""
import argparse
import json
import sys
from pathlib import Path

from epc_pv import Options, PvError, run


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="epc_pv", description="Hourly energy yield and string layout of the arrays of a JSON document.")
    ap.add_argument("input")
    ap.add_argument("--out", required=True)
    ap.add_argument("--transposition", default="haydavies", choices=("haydavies", "isotropic"))
    a = ap.parse_args(argv)
    try:
        result = run(Path(a.input).read_bytes(), Options(transposition=a.transposition))
    except PvError as e:
        print(f"ERROR {e.en}", file=sys.stderr)
        print(f"ERROR (es) {e.es}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 1
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "pv_yield.json").write_text(json.dumps(result.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
