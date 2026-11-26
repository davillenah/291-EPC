"""Adds block placeholder symbols (a box with the device name) to the SLD LV library: SVG, DXF block and catalog entry.

Placeholder rule (owner, 2026-11-21): a device without a real IEC 60617 symbol is drawn as a box with its name,
always as a block (named like the file, one ATTDEF per label slot), until the real symbol replaces it.
Run: python add_block_placeholders.py   (idempotent: a symbol already in the catalog is left as it is)
"""
import json
import pathlib

import ezdxf

LIB = pathlib.Path(__file__).resolve().parents[2] / "src" / "epc_draw" / "symbols" / "library" / "sld-lv-symbol"
PREFIX = "291_E_LV_SLD_IEC60617_"
W, H, STUB = 24.0, 20.0, 2.5      # box width, port to port height, stub length (mm; ports on the 2.5 mm grid)
BLUE = "#0000ff"
# id, file stem, box text, name_es, name_en, research device id
PLACEHOLDERS = [
    ("lv_imd", "imd", "IMD", "Monitor de aislación (IMD)", "Insulation monitoring device (IMD)", "imd_insulation_monitor"),
    ("lv_pv_blocking_diode", "pv_blocking_diode", "DIODO", "Diodo de bloqueo FV", "PV blocking diode", "pv_blocking_diode"),
    ("lv_pv_power_optimizer", "pv_power_optimizer", "OPTIM", "Optimizador de potencia FV", "PV power optimizer", "pv_power_optimizer"),
    ("lv_pv_rapid_shutdown", "pv_rapid_shutdown", "RSD", "Dispositivo de corte rápido FV", "PV rapid shutdown device", "pv_rapid_shutdown_device"),
    ("lv_pv_rcmu", "pv_rcmu", "RCMU", "Monitor de corriente residual (RCMU)", "Residual current monitoring unit (RCMU)", "pv_rcmu"),
    ("lv_pv_combiner_box", "pv_combiner_box", "CAJA STR", "Caja combinadora de strings FV", "PV string combiner box", "pv_string_combiner_box"),
]


def svg(sid, text, name_es, name_en):
    vb = (-W / 2 - 14.0, -1.6, W + 14.0 + 14.0, H + 3.2)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb[0]} {vb[1]} {vb[2]} {vb[3]}" width="{vb[2]}mm" height="{vb[3]}mm" role="img" aria-label="{name_es}">
  <title>{name_es}</title>
  <desc>Placeholder block: a box with the device name until the real IEC 60617 symbol exists. | Bloque provisorio: caja con el nombre del dispositivo hasta que exista el símbolo IEC 60617 real.</desc>
  <g id="{sid}" fill="none" stroke-linecap="butt" stroke-linejoin="round" font-family="Arial, sans-serif">
    <line x1="0" y1="0" x2="0" y2="{STUB}" stroke="{BLUE}" stroke-width="0.25" />
    <rect x="{-W / 2}" y="{STUB}" width="{W}" height="{H - 2 * STUB}" stroke="{BLUE}" stroke-width="0.25" />
    <text x="0" y="{H / 2 + 0.9}" font-size="2.5" fill="{BLUE}" text-anchor="middle">{text}</text>
    <line x1="0" y1="{H - STUB}" x2="0" y2="{H}" stroke="{BLUE}" stroke-width="0.25" />
  </g>
  <g id="ports" display="none" fill="#ff00ff" stroke="none">
    <circle id="port_top" cx="0" cy="0" r="0.6" data-dir="up" />
    <circle id="port_bottom" cx="0" cy="{H}" r="0.6" data-dir="down" />
  </g>
  <g id="label_slots" fill="#008800" font-family="Arial, sans-serif">
    <text id="slot_tag" data-key="tag" data-example="-X1" x="{-W / 2 - 2}" y="{H / 2}" font-size="2.5" text-anchor="end" fill="{BLUE}">{{tag}}</text>
  </g>
</svg>
'''


def dxf(path, block, text):
    doc = ezdxf.new("R2000")
    b = doc.blocks.new(name=block)
    kw = {"layer": "0", "true_color": 255}                      # blue (0x0000ff)
    b.add_line((0, 0), (0, -STUB), dxfattribs=kw)
    b.add_lwpolyline([(-W / 2, -STUB), (W / 2, -STUB), (W / 2, -(H - STUB)), (-W / 2, -(H - STUB))], close=True, dxfattribs=kw)
    b.add_text(text, height=2.5, dxfattribs={**kw, "insert": (0, -(H / 2 + 0.9)), "halign": 1, "align_point": (0, -(H / 2 + 0.9))})
    b.add_line((0, -(H - STUB)), (0, -H), dxfattribs=kw)
    b.add_attdef("TAG", (-W / 2 - 2, -H / 2), text="Tag", dxfattribs={**kw, "height": 2.5})
    doc.saveas(path)


def main():
    cat_path = LIB / "_catalog.json"
    cat = json.loads(cat_path.read_text(encoding="utf-8"))
    have = {s["id"] for s in cat["symbols"]}
    vb = {"x": -W / 2 - 14.0, "y": -1.6, "w": W + 28.0, "h": H + 3.2}
    for sid, stem, text, name_es, name_en, dev in PLACEHOLDERS:
        if sid in have:
            continue
        (LIB / f"{PREFIX}{stem}.svg").write_text(svg(sid, text, name_es, name_en), encoding="utf-8")
        dxf(str(LIB / f"{PREFIX}{stem}.dxf"), f"{PREFIX}{stem}", text)
        cat["symbols"].append({
            "id": sid, "file": f"{PREFIX}{stem}.svg", "name_es": name_es, "name_en": name_en,
            "description": "Bloque provisorio (caja con el nombre) hasta que exista el símbolo real. / Placeholder block until the real symbol exists.",
            "tags": ["placeholder", dev], "origin": "placeholder", "source": "Bloque provisorio EPC-291 (DGM-03)", "notes": None,
            "size": {"w": vb["w"], "h": vb["h"]}, "viewBox": vb,
            "ports": [{"id": "top", "x": 0.0, "y": 0.0, "dir": "up"}, {"id": "bottom", "x": 0.0, "y": H, "dir": "down"}],
            "fixed_texts": [text],
            "label_slots": [{"key": "tag", "placeholder": "{tag}", "example": "-X1", "x": -W / 2 - 2, "y": H / 2, "anchor": "end", "size": 3.47}],
        })
    cat_path.write_text(json.dumps(cat, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
