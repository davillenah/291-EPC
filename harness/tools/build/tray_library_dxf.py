"""Write the tray parts library as DXF files, one per piece, plus one sheet with all of them side by side: `python harness/tools/build/tray_library_dxf.py <folder> [width_mm] [height_mm]`.

This is the caller of the engine: `epc_plan.tray_pieces` gives the pieces as data, this tool writes them (an engine never writes files). File names are the codes in lower snake_case.
"""
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "harness" / "src")] + [str(p) for p in sorted((ROOT / "harness" / "src" / "engines").glob("*/*/src"))]

import epc_plan   # noqa: E402


def file_name(code: str) -> str:
    return code.lower().replace("-", "_") + ".dxf"


def _width(it: Dict[str, Any]) -> float:
    xs = [v[0] for v in it["mesh"]["vertices"]]
    return max(xs) - min(xs) if xs else 0.0


def _moved(it: Dict[str, Any], dx: float, dy: float) -> Dict[str, Any]:
    xs = [v[0] for v in it["mesh"]["vertices"]]
    shift = dx - (min(xs) if xs else 0.0)
    mesh = {"vertices": [[v[0] + shift, v[1] + dy, v[2]] for v in it["mesh"]["vertices"]], "faces": it["mesh"]["faces"]}
    return dict(it, mesh=mesh, path=[[p[0] + shift, p[1] + dy, p[2]] for p in it["path"]])


def _grid(items: List[Dict[str, Any]], gap: float = 1.0) -> List[Dict[str, Any]]:
    """The pieces laid out in rows by group and kind, so one sheet shows all of them."""
    rows: Dict[str, List[Dict[str, Any]]] = {}
    for it in items:
        rows.setdefault(it["group"] + it["code"].split("-")[1], []).append(it)
    placed = []
    for n, row in enumerate(rows.values()):
        x = 0.0
        for it in row:
            placed.append(_moved(it, x, n * 1.5))
            x += _width(it) + gap
    return placed


def main(argv: List[str]) -> int:
    out = Path(argv[1])
    width = float(argv[2]) / 1000 if len(argv) > 2 else 0.3
    height = float(argv[3]) / 1000 if len(argv) > 3 else 0.09
    items = epc_plan.tray_pieces(width, height)
    out.mkdir(parents=True, exist_ok=True)
    warnings: List[str] = []
    for it in items:
        warnings += epc_plan.write_dxf_3d([it], out / file_name(it["code"]))
    warnings += epc_plan.write_dxf_3d(_grid(items), out / "all_pieces.dxf")
    print(f"{len(items)} pieces written to {out}; {len(warnings)} warnings")
    for w in warnings[:10]:
        print(w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
