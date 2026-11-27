"""A plan of the plan editor (iluminación, tomacorrientes, bandejas...) drawn on the IRAM sheet of its format with the title block of the project: the DXF of the plan is placed, at a standard scale, in the free
zone of the sheet that `epc_titleblock` makes (above the title block and the list of modifications), and the sheet keeps its frame, its title block and its logos.

  python -m epc_drawing.export.plan_sheet PLAN.dxf REQUEST.json OUT.dxf [--format A1] [--scale 100]

`REQUEST.json` is the request of `epc_titleblock.service` (the project's common fields and its logos); its sheet is made here, one for the plan. The result says the format and the scale used: a plan that does
not fit at the scale asked takes the next smaller standard one."""
import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from epc_drawing.errors import DrawingError

STANDARD_SCALES = (1, 2, 5, 10, 20, 25, 50, 75, 100, 125, 150, 200, 250, 500, 750, 1000, 1500, 2000, 5000)
FORMATS = ("A0", "A1", "A2", "A3", "A4")
GAP = 5.0                                         # mm of clear paper between the plan and the frame or the title block
UNIT_MM = {4: 1.0, 5: 10.0, 6: 1000.0}            # DXF $INSUNITS code -> mm per unit (millimetres, centimetres, metres)
Box = Tuple[float, float, float, float]


def _box(attr: Optional[str]) -> Optional[Box]:
    v = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", attr or "")]
    return (v[0], v[1], v[2], v[3]) if len(v) == 4 else None


def free_area(svg: str) -> Tuple[Box, float]:
    """The zone of the sheet for the drawing (x0, y0, x1, y1 in mm, y down as in the SVG) and the height of the sheet: the usable zone less the title block and the list of modifications, with a clear gap."""
    head = re.search(r"<svg[^>]*>", svg).group(0)
    zone = _box(re.search(r'data-zona-util="([^"]+)"', head).group(1) if "data-zona-util" in head else None)
    if zone is None:
        raise DrawingError("err_sheet_no_zone")
    height = float(re.search(r'height="([\d.]+)mm"', head).group(1))
    blocks = [b for b in (_box(re.search(r'data-rotulo="([^"]+)"', head).group(1) if "data-rotulo" in head else None),
                          _box(re.search(r'data-modificaciones="([^"]+)"', head).group(1) if "data-modificaciones" in head else None)) if b]
    bottom = min([zone[3]] + [b[1] for b in blocks])
    return (zone[0] + GAP, zone[1] + GAP, zone[2] - GAP, bottom - GAP), height


def fit_scale(extent_mm: Tuple[float, float], area: Box, asked: Optional[int]) -> int:
    """The standard scale (denominator) at which a plan of `extent_mm` real millimetres fits the area: the one asked when it fits, else the largest that does (the plan is smaller than the paper at 1:N)."""
    w, h = max(extent_mm[0], 1e-6), max(extent_mm[1], 1e-6)
    aw, ah = area[2] - area[0], area[3] - area[1]
    fits = [s for s in STANDARD_SCALES if w / s <= aw and h / s <= ah]
    if not fits:
        return STANDARD_SCALES[-1]
    return asked if asked in fits else (min(fits) if asked is None else min([s for s in fits if s >= asked] or [max(fits)]))


def _extents(msp) -> Optional[Tuple[float, float, float, float]]:
    from ezdxf import bbox
    box = bbox.extents(msp, fast=True)
    return None if not box.has_data else (box.extmin.x, box.extmin.y, box.extmax.x, box.extmax.y)


def _sheet_dxf(request: dict, fmt: str, name: str, scale: int, tmp: Path) -> Tuple[Path, str]:
    """The sheet of the format as a DXF (frame, title block and logos) with the scale in its title block, and its SVG."""
    from epc_dxf import deliverable
    from epc_titleblock import service
    sheet = {"name": name, "format": fmt, "fields": {"escala": f"1:{scale}"}}
    result = service.render({**request, "sheets": [sheet]})
    svg_path = tmp / "sheet.svg"
    svg_path.write_text(result["sheets"][0]["svg"], encoding="utf-8")
    done = deliverable.convert(svg_path, tmp / "sheet.dxf")
    if not done.get("dxf"):
        raise DrawingError("err_sheet_not_dxf", reason='; '.join(done.get('messages') or []))
    return Path(done["dxf"]), result["sheets"][0]["svg"]


def _keep_transparency(plan, sheet) -> None:
    """The importer copies the layers without their transparency (an extended-data record): the sheet gives each layer the transparency it has in the plan (PV-18: the disk grid at 80 %)."""
    for lay in plan.layers:
        if lay.transparency > 0 and lay.dxf.name in sheet.layers:
            sheet.layers.get(lay.dxf.name).transparency = lay.transparency


def compose(plan_dxf: Path, request: dict, out_dxf: Path, fmt: str = "A1", scale: Optional[int] = None, name: str = "PLAN") -> Dict[str, object]:
    """Draw the plan on the sheet and save it as `out_dxf`; returns {"format", "scale", "dxf"}."""
    import ezdxf
    from ezdxf.addons.importer import Importer
    from ezdxf.math import Matrix44
    if fmt not in FORMATS:
        raise DrawingError("err_format_invalid", formats=', '.join(FORMATS))
    plan = ezdxf.readfile(str(plan_dxf))
    ext = _extents(plan.modelspace())
    if ext is None:
        raise DrawingError("err_plan_empty")
    mm_per_unit = UNIT_MM.get(int(plan.header.get("$INSUNITS", 6)), 1000.0)
    with tempfile.TemporaryDirectory() as tmp:
        first, svg = _sheet_dxf(request, fmt, name, scale or 100, Path(tmp))
        area, height = free_area(svg)
        real_mm = ((ext[2] - ext[0]) * mm_per_unit, (ext[3] - ext[1]) * mm_per_unit)
        used = fit_scale(real_mm, area, scale)
        sheet_path = first
        if used != (scale or 100):
            sheet_path, svg = _sheet_dxf(request, fmt, name, used, Path(tmp))
            area, height = free_area(svg)
        sheet = ezdxf.readfile(str(sheet_path))
        msp = sheet.modelspace()
        before = {e.dxf.handle for e in msp}
        importer = Importer(plan, sheet)
        importer.import_modelspace()
        importer.finalize()
        _keep_transparency(plan, sheet)
        k = mm_per_unit / used                                                         # paper millimetres per plan unit
        cx, cy = (area[0] + area[2]) / 2.0, height - (area[1] + area[3]) / 2.0          # centre of the free zone, in DXF coordinates (y up)
        move = Matrix44.translate(-(ext[0] + ext[2]) / 2.0, -(ext[1] + ext[3]) / 2.0, 0) @ Matrix44.scale(k, k, k) @ Matrix44.translate(cx, cy, 0)
        for e in list(msp):
            if e.dxf.handle not in before:
                e.transform(move)
        sheet.units = 4
        Path(out_dxf).parent.mkdir(parents=True, exist_ok=True)
        sheet.saveas(str(out_dxf))
    return {"format": fmt, "scale": used, "dxf": str(out_dxf)}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="epc_drawing.export.plan_sheet")
    ap.add_argument("plan")
    ap.add_argument("request")
    ap.add_argument("out")
    ap.add_argument("--format", default="A1")
    ap.add_argument("--scale", type=int, default=None)
    ap.add_argument("--name", default="PLAN")
    a = ap.parse_args(argv)
    try:
        res = compose(Path(a.plan), json.loads(Path(a.request).read_text(encoding="utf-8")), Path(a.out), a.format, a.scale, a.name)
    except (ValueError, RuntimeError, OSError) as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 1
    print(f"OK {res['format']} 1:{res['scale']} -> {res['dxf']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
