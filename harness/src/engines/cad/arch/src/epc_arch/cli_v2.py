"""python -m epc_arch.cli_v2 PLAN --out DIR [--formats svg,dxf,png,pdf] [--sheet A1] [--scale 100] [--dpi 300]

Reads the plan with the current engine and writes it with the v2 exporters, one set of files per floor: `<stem>.<level>.plan.<ext>`. Also writes `run_manifest.json`."""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from epc_arch import ArchError, Options, __version__
from epc_arch.drawing import STYLE_PATH
from epc_arch.drawing import build_drawing, style_with
from epc_arch.export.export_dxf import to_dxf
from epc_arch.export.export_raster import to_pdf, to_png
from epc_arch.export.export_svg import to_svg
from epc_arch.export.sheet_iram import load_template
from epc_arch.sheets import DEFAULT_FORMAT, iram_template
from epc_arch.pipeline import recognize_sheet

WRITERS = {"svg": lambda d, a: to_svg(d, a.style_obj).encode("utf-8"), "dxf": lambda d, a: to_dxf(d, a.style_obj).encode("utf-8"), "png": lambda d, a: to_png(d, a.style_obj, dpi=a.dpi), "pdf": lambda d, a: to_pdf(d, a.style_obj)}


def _tag(result, position: int) -> str:
    level = result.architecture.level
    return f"L{level.index}" if level and level.index is not None else f"plan{position}"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _template(a):
    """The sheet to draw on and where it came from: the SVG the caller gave, else the IRAM sheet of the format (A1 by default), else, when `epc_titleblock` is not there or `--no-iram` is given,
    the engine's own frame."""
    if a.sheet_svg:
        return load_template(Path(a.sheet_svg).read_text(encoding="utf-8")), "given"
    if a.no_iram:
        return None, "engine-frame"
    found = iram_template(a.sheet or DEFAULT_FORMAT, a.sheet_config_obj)
    if found is None:
        print("WARNING no IRAM sheet could be made (epc_titleblock not found): the plan is drawn on the engine's own frame", file=sys.stderr)
        return None, "engine-frame"
    return found, "iram-default"


def fields_of(a) -> dict:
    return dict(f.split("=", 1) for f in a.field if "=" in f)


def _manifest(src: Path, data: bytes, a, formats, outputs, out: Path, sheet_source: str = "engine-frame") -> dict:
    """What a run was: the engine, the input and the files that set how it was read and drawn (params, style) by hash, the options, and each output by hash."""
    here = Path(__file__).parent
    return {"engine": "epc_arch", "version": __version__, "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "input": {"name": src.name, "sha256": hashlib.sha256(data).hexdigest()}, "params_sha256": _sha(here / "params.json"), "style_sha256": _sha(STYLE_PATH),
            "options": {"formats": formats, "sheet": a.sheet, "sheet_source": sheet_source, "scale": a.scale, "dpi": a.dpi, "page": a.page, "sheet_svg_sha256": _sha(Path(a.sheet_svg)) if a.sheet_svg else None, "fields": fields_of(a)}, "outputs": [{"file": n, "sha256": _sha(out / n)} for n in outputs]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="epc_arch.cli_v2")
    ap.add_argument("plan")
    ap.add_argument("--out", default="out/v2")
    ap.add_argument("--formats", default="svg,dxf,png,pdf")
    ap.add_argument("--sheet", default=None, help="sheet format A0..A4 (A1 by default)")
    ap.add_argument("--no-iram", action="store_true", help="draw on the engine's own simple frame instead of an IRAM sheet")
    ap.add_argument("--scale", type=int, default=None)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--sheet-svg", default=None, help="an IRAM sheet (SVG of epc_titleblock) to draw the plan on; its size and title block are used")
    ap.add_argument("--field", action="append", default=[], metavar="KEY=VALUE", help="a field of the title block of --sheet-svg (escala, denominacion, proyecto...)")
    ap.add_argument("--style", default=None, help="JSON with the pens, the pen of each layer and the text heights the organization changed (see `drawing.style_with`)")
    ap.add_argument("--sheet-config", default=None, help="JSON with how the organization changed the IRAM sheet of the format (see `epc_titleblock.layout`)")
    a = ap.parse_args(argv)
    try:
        a.style_obj = style_with(json.loads(Path(a.style).read_text(encoding="utf-8")) if a.style else None)
        a.sheet_config_obj = json.loads(Path(a.sheet_config).read_text(encoding="utf-8")) if a.sheet_config else None
    except (OSError, ValueError) as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 1
    src, out = Path(a.plan), Path(a.out)
    formats = [f.strip() for f in a.formats.split(",") if f.strip()]
    if any(f not in WRITERS for f in formats):
        print("ERROR formats must be among " + ",".join(WRITERS), file=sys.stderr)
        return 1
    data = src.read_bytes()
    try:
        sheet = recognize_sheet(data, src.name, Options(page=a.page, background=False))
    except ArchError as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 1
    template, sheet_source = _template(a)
    fields = dict(f.split("=", 1) for f in a.field if "=" in f)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for i, r in enumerate(sheet.levels, 1):
        d = build_drawing(r.architecture, sheet=a.sheet or (DEFAULT_FORMAT if not template else None), scale=a.scale, document=src.name, template=template, fields=fields, style=a.style_obj)
        for f in formats:
            name = f"{src.stem}.{_tag(r, i)}.plan.{f}"
            (out / name).write_bytes(WRITERS[f](d, a))
            written.append(name)
    manifest = _manifest(src, data, a, formats, written, out, sheet_source)
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(f"OK {len(sheet.levels)} plan(s) -> {out}: {', '.join(written)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
