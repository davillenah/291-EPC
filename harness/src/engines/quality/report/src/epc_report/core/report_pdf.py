"""Render a structured report (title, key/value blocks, headings, paragraphs, bullet lists, tables) to an A4 PDF with matplotlib.

The caller supplies every text; this module has no wording of its own (management reports in any language and methodology).

  python -m epc_report.core.report_pdf <report.json> <out.pdf>

report = {"title": "Informe de Estado", "subtitle": "STATUS-01", "footer": "...", "page_label": "Página {n} de {total}",
          "blocks": [{"type": "kv", "rows": [["Proyecto", "..."]]},
                     {"type": "h", "text": "Estado general"},
                     {"type": "p", "text": "..."},
                     {"type": "bullets", "items": ["..."]},
                     {"type": "table", "columns": [["Hito", 0.4], ["Fecha", 0.2], ...], "rows": [[...]], "empty": "Sin registros"},
                     {"type": "figure", "title": "...", "caption": "...", "bounds": [x0, y0, x1, y1], "max_height": 300,
                      "shapes": [{"s": "poly", "points": [[x, y], ...], "fill": "#rrggbb" | null, "stroke": "#rrggbb", "lw": 0.8}, {"s": "rect", "x": 0, "y": 0, "w": 1, "h": 1, "fill": "#rrggbb"},
                                 {"s": "circle", "x": 0, "y": 0, "r": 1, "fill": "#rrggbb" | null, "stroke": "#rrggbb"}, {"s": "line", "points": [[x, y], [x, y]], "stroke": "#rrggbb", "lw": 0.8},
                                 {"s": "text", "x": 0, "y": 0, "text": "...", "size": 8, "color": "#rrggbb"}]}]}

A figure is drawn from shapes in the coordinates of whatever it shows (a plan, in its own units, y growing downwards): it is scaled to the width of the page, or to `max_height`, whichever is smaller.
"""
import json
import sys
import textwrap
from pathlib import Path
from typing import List

W, H = 595.0, 842.0
M = 50.0
FS, FS_SMALL = 9.0, 8.0
CHAR = 0.56
LINE = 12.0
BOTTOM = H - 62


def _wrap(text, width_pt: float, size: float) -> List[str]:
    chars = max(int(width_pt / (CHAR * size)), 4)
    lines: List[str] = []
    for part in str(text).split("\n"):
        lines += textwrap.wrap(part, chars, break_long_words=True) or [""]
    return lines


def _shape(s: dict, at, scale: float, ops) -> None:
    """One shape of a figure as the drawing operations of the page."""
    kind = s.get("s")
    if kind == "poly":
        ops().append(("poly", [at(*p) for p in s["points"]], s.get("fill"), s.get("stroke"), float(s.get("lw", 0.8))))
    elif kind == "rect":
        x, y = at(s["x"], s["y"])
        ops().append(("rect", x, y, s["w"] * scale, s["h"] * scale, s["fill"]))
    elif kind == "circle":
        x, y = at(s["x"], s["y"])
        ops().append(("circle", x, y, s["r"] * scale, s.get("fill"), s.get("stroke"), float(s.get("lw", 0.8))))
    elif kind == "line":
        (xa, ya), (xb, yb) = at(*s["points"][0]), at(*s["points"][1])
        ops().append(("line", xa, ya, xb, yb, float(s.get("lw", 0.8)), s.get("stroke", "#000000")))
    elif kind == "text":
        x, y = at(s["x"], s["y"])
        ops().append(("text", x, y, s["text"], float(s.get("size", 8)), "bold" if s.get("bold") else "normal", s.get("color", "#000000"), s.get("align", "left")))


def _logo_size(path: str, box_w: float, box_h: float):
    """The size a logo takes inside a box (its proportions kept); None when the file cannot be read as an image."""
    from epc_report.core import logo
    im = logo.image(path)                                                                # PNG, JPEG or SVG; an unreadable logo is left out, never a failed report
    if im is None:
        return None
    w, h = im.size
    scale = min(box_w / max(w, 1), box_h / max(h, 1))
    return w * scale, h * scale


def logo_data(logo):
    from epc_report.core import logo as _logo
    return _logo.data_of(logo)


def cover_ops(cover: dict, rep: dict) -> list:
    """The first page of a report: the logos of the issuer and of the client, the title, the document and its data (`cover` = {"logos": [path, path], "rows": [[label, value]]})."""
    ops = [("line", M, 120, W - M, 120, 0.8, "#808080")]
    for k, path in enumerate((cover.get("logos") or [])[:2]):
        size = _logo_size(path, 150, 60) if path else None
        if size:
            x = M if k == 0 else W - M - size[0]
            ops.append(("image", x, 120 - 12 - size[1], size[0], size[1], path if logo_data(path) is not None else str(path)))
    ops.append(("text", M, 300, rep.get("title", ""), 26, "bold", "#000000", "left"))
    ops.append(("text", M, 330, rep.get("subtitle", ""), 15, "bold", "#000000", "left"))
    ops.append(("line", M, 345, W - M, 345, 1.4, "#000000"))
    y = 380.0
    for label, value in cover.get("rows") or []:
        ops.append(("text", M, y, str(label), FS, "bold", "#000000", "left"))
        ops.append(("text", M + 150, y, str(value), 11, "normal", "#000000", "left"))
        y += 24
    return ops


def _first_pages(rep: dict) -> List[list]:
    """The pages a report starts with: the cover (page 1) and an empty page for the text, or just the empty page."""
    return [cover_ops(rep["cover"], rep), []] if rep.get("cover") else [[]]


def layout(rep: dict) -> List[list]:
    pages: List[list] = _first_pages(rep)
    y = M
    tw = W - 2 * M

    def ops():
        return pages[-1]

    def need(h):
        nonlocal y
        if y + h > BOTTOM:
            pages.append([])
            y = M
            return True
        return False

    ops().append(("text", M, y + 14, rep.get("title", ""), 17, "bold", "#000000", "left"))
    ops().append(("text", W - M, y + 14, rep.get("subtitle", ""), 14, "bold", "#000000", "right"))
    y += 26
    ops().append(("line", M, y, W - M, y, 1.4, "#000000"))
    y += 14

    def _bullets(items, y):
        for item in items:
            lines = _wrap(item, tw - 14, FS)
            if need(len(lines) * LINE):                                               # a new page starts at the top: the caller's y is not the one of the page any more
                y = M
            ops().append(("text", M + 2, y + 9, "•", FS, "normal", "#000000", "left"))
            for i, line in enumerate(lines):
                ops().append(("text", M + 14, y + 9 + i * LINE, line, FS, "normal", "#000000", "left"))
            y += len(lines) * LINE
        return y + 6

    def _figure(b, ops, need, y, tw):
        x0, y0, x1, y1 = b["bounds"]
        bw, bh = max(x1 - x0, 1e-9), max(y1 - y0, 1e-9)
        scale = min(tw / bw, float(b.get("max_height", 300)) / bh)
        height = bh * scale
        heading = 24 if b.get("title") else 0                                          # the heading is part of the figure: it never stays alone at the foot of a page
        if need(height + 30 + heading):
            y = M
        if heading:
            ops().append(("text", M, y + 17, b["title"], 11.5, "bold", "#000000", "left"))
        top = y + heading
        at = lambda px, py: (M + (px - x0) * scale, top + (py - y0) * scale)               # noqa: E731
        ops().append(("rect", M, top, bw * scale, height, "#fbfbfd"))
        for s in b.get("shapes", []):
            _shape(s, at, scale, ops)
        y = top + height + 4
        for line in _wrap(b["caption"], tw, FS_SMALL) if b.get("caption") else []:        # a long caption goes on several lines
            ops().append(("text", M, y + 9, line, FS_SMALL, "italic", "#000000", "left"))
            y += LINE
        return y + 8

    def table_header(cols, xs):
        nonlocal y
        ops().append(("rect", M, y, tw, 20, "#d9d9d9"))
        for (label, _), x in zip(cols, xs):
            ops().append(("text", x + 4, y + 13.5, label, FS_SMALL, "bold", "#000000", "left"))
        y += 20

    for b in rep.get("blocks", []):
        kind = b.get("type")
        if kind == "kv":
            for label, value in b["rows"]:
                lines = _wrap(value, W - M - 190, FS)
                need(len(lines) * LINE + 4)
                ops().append(("text", M, y + 9, label, FS_SMALL, "bold", "#000000", "left"))
                for i, line in enumerate(lines):
                    ops().append(("text", 190, y + 9 + i * LINE, line, FS, "normal", "#000000", "left"))
                y += max(len(lines), 1) * LINE + 3
            y += 8
        elif kind == "h":
            need(60)
            y += 6
            ops().append(("text", M, y + 11, b["text"], 11.5, "bold", "#000000", "left"))
            y += 18
        elif kind == "p":
            for line in _wrap(b["text"], tw, FS):
                need(LINE)
                ops().append(("text", M, y + 9, line, FS, "normal", "#000000", "left"))
                y += LINE
            y += 6
        elif kind == "bullets":
            y = _bullets(b["items"], y)
        elif kind == "figure":
            y = _figure(b, ops, need, y, tw)
        elif kind == "table":
            cols = b["columns"]
            xs = [M]
            for _, share in cols:
                xs.append(xs[-1] + share * tw)
            rows = b.get("rows", [])
            if not rows:
                need(30)
                ops().append(("text", M, y + 9, b.get("empty", "-"), FS, "italic", "#000000", "left"))
                y += LINE + 8
                continue
            need(20 + 30)
            table_header(cols, xs)
            for row in rows:
                cells = [_wrap(c, (xs[i + 1] - xs[i]) - 8, FS) for i, c in enumerate(row)]
                h = max(len(c) for c in cells) * LINE + 8
                if need(h):
                    table_header(cols, xs)
                for i, lines in enumerate(cells):
                    for j, line in enumerate(lines):
                        ops().append(("text", xs[i] + 4, y + 13 + j * LINE, line, FS, "normal", "#000000", "left"))
                y += h
                ops().append(("line", M, y, W - M, y, 0.5, "#808080"))
            y += 10
    total = len(pages)
    for n, p in enumerate(pages, 1):
        p.append(("line", M, H - 44, W - M, H - 44, 0.5, "#808080"))
        p.append(("text", M, H - 30, rep.get("footer", ""), FS_SMALL, "normal", "#000000", "left"))
        p.append(("text", W - M, H - 30, rep.get("page_label", "{n}/{total}").format(n=n, total=total), FS_SMALL, "normal", "#000000", "right"))
    return pages


def _paint_text(ax, op, patches) -> None:
    _, x, y, text, size, weight, color, ha = op
    ax.text(x, y, text, fontsize=size, fontweight="bold" if weight == "bold" else "normal", fontstyle="italic" if weight == "italic" else "normal", color=color, ha=ha, va="baseline")


def _paint_line(ax, op, patches) -> None:
    _, x1, y1, x2, y2, lw, color = op
    ax.plot([x1, x2], [y1, y2], color=color, linewidth=lw, solid_capstyle="butt")


def _paint_poly(ax, op, patches) -> None:
    _, pts, fill, stroke, lw = op
    ax.add_patch(patches.Polygon(pts, closed=True, facecolor=fill or "none", edgecolor=stroke or "none", linewidth=lw))


def _paint_circle(ax, op, patches) -> None:
    _, x, y, r, fill, stroke, lw = op
    ax.add_patch(patches.Circle((x, y), r, facecolor=fill or "none", edgecolor=stroke or "none", linewidth=lw))


def _paint_rect(ax, op, patches) -> None:
    _, x, y, w, h, color = op
    ax.add_patch(patches.Rectangle((x, y), w, h, facecolor=color, edgecolor="none"))


def _paint_image(ax, op, patches) -> None:
    _, x, y, w, h, path = op
    import numpy as np
    from epc_report.core import logo
    im = logo.image(path)
    if im is None:
        return
    ax.imshow(np.asarray(im), extent=(x, x + w, y + h, y), aspect="auto", zorder=1)
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)


_PAINTERS = {"image": _paint_image, "text": _paint_text, "line": _paint_line, "poly": _paint_poly, "circle": _paint_circle, "rect": _paint_rect}       # operation of a page -> how it is drawn


def figure_png(b: dict, width_pt: float = 480.0):
    """(png bytes, width, height in points) of a figure block drawn on its own (what a Word document carries in place of the page drawing)."""
    import io
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Liberation Sans", "Helvetica", "DejaVu Sans"], "text.color": "#000000"})
    from matplotlib import patches
    x0, y0, x1, y1 = b["bounds"]
    bw, bh = max(x1 - x0, 1e-9), max(y1 - y0, 1e-9)
    scale = min(width_pt / bw, float(b.get("max_height", 300)) / bh)
    w, h = bw * scale, bh * scale
    ops: list = []
    at = lambda px, py: ((px - x0) * scale, (py - y0) * scale)                              # noqa: E731
    for shape in b.get("shapes", []):
        _shape(shape, at, scale, lambda: ops)
    fig = plt.figure(figsize=(w / 72, h / 72))
    try:
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, w)
        ax.set_ylim(h, 0)
        ax.axis("off")
        for op in ops:
            _PAINTERS.get(op[0], _paint_rect)(ax, op, patches)
        out = io.BytesIO()
        fig.savefig(out, format="png", dpi=200, facecolor="#ffffff")
    finally:
        plt.close(fig)
    return out.getvalue(), w, h


def render_bytes(rep: dict, date=None) -> bytes:
    """The PDF of a report as bytes; nothing is written. `date` (a datetime) is the creation date of the file: given, the same report always gives the same bytes; without it the clock is used (as `render` did)."""
    import io
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Liberation Sans", "Helvetica", "DejaVu Sans"], "text.color": "#000000"})
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib import patches

    pages = layout(rep)
    metadata = {"Title": f"{rep.get('title', '')} {rep.get('subtitle', '')}".strip()}
    if date is not None:
        metadata.update({"CreationDate": date, "ModDate": date})
    out = io.BytesIO()
    with PdfPages(out, metadata=metadata) as pdf:
        for page in pages:
            fig = plt.figure(figsize=(W / 72, H / 72))
            try:
                ax = fig.add_axes([0, 0, 1, 1])
                ax.set_xlim(0, W)
                ax.set_ylim(H, 0)
                ax.axis("off")
                for op in page:
                    _PAINTERS.get(op[0], _paint_rect)(ax, op, patches)
                pdf.savefig(fig, facecolor="white")
            finally:
                plt.close(fig)
    return out.getvalue()


def render(rep: dict, dst: Path) -> Path:
    """The PDF of a report written to `dst` (a thin caller of `render_bytes`; the engine itself writes nothing)."""
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    Path(dst).write_bytes(render_bytes(rep))
    return Path(dst)


def _render_job(job):
    report, dst = job
    return render(report, Path(dst))


def render_many(jobs, workers=None) -> List[Path]:
    """The PDFs of several reports, `jobs` = [(report, dst)], returned in the same order (OPT-06).

    matplotlib is not thread-safe, so the reports go to separate processes (started with `spawn`, the same on every system); one report, one worker or one core renders in this
    process. Every file is the one `render` would write: a process only changes who draws it.
    """
    import os
    jobs = [(report, str(dst)) for report, dst in jobs]
    count = min(workers or 4, os.cpu_count() or 1, len(jobs))
    if count < 2:
        return [_render_job(job) for job in jobs]
    import concurrent.futures
    import multiprocessing
    with concurrent.futures.ProcessPoolExecutor(max_workers=count, mp_context=multiprocessing.get_context("spawn")) as pool:
        return list(pool.map(_render_job, jobs))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    render(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")), Path(sys.argv[2]))
    print("OK", sys.argv[2])
