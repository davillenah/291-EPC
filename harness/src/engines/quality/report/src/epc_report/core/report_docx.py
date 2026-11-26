"""Render a structured report (the same one `report_pdf` takes: title, cover, key/value blocks, headings, paragraphs, bullets, tables) to a Word document (.docx), without any library: a .docx is a zip of XML parts.

  python -m epc_report.core.report_docx <report.json> <out.docx>

Styles are the ones Word has by name (Title, Heading 1, Table Grid), so the person edits it with the usual tools. A cover is the first page (logos that are PNG or JPEG, title, the data of the document) followed by a page break;
the footer says the text of the report and «Page n of total» with Word's own fields."""
import json
import sys
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple
from xml.sax.saxutils import escape

EMU_PER_PT = 12700
PAGE_W_TW = 11906 - 2 * 1134                    # A4 width minus 2 cm margins, in twentieths of a point
NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')

STYLES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles {NS}>
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="20"/><w:lang w:val="es-AR"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="100" w:line="264" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="120"/></w:pPr><w:rPr><w:b/><w:sz w:val="44"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:rPr><w:b/><w:color w:val="1F4E8C"/><w:sz w:val="30"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="280" w:after="100"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:color w:val="1F4E8C"/><w:sz w:val="28"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListBullet"><w:name w:val="List Bullet"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:ind w:left="360" w:hanging="260"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Footer"><w:name w:val="footer"/><w:basedOn w:val="Normal"/><w:rPr><w:color w:val="777777"/><w:sz w:val="16"/></w:rPr></w:style>
<w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/><w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>
<w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/><w:basedOn w:val="TableNormal"/><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4" w:space="0" w:color="C8CDD5"/><w:left w:val="single" w:sz="4" w:space="0" w:color="C8CDD5"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="C8CDD5"/><w:right w:val="single" w:sz="4" w:space="0" w:color="C8CDD5"/><w:insideH w:val="single" w:sz="4" w:space="0" w:color="C8CDD5"/><w:insideV w:val="single" w:sz="4" w:space="0" w:color="C8CDD5"/></w:tblBorders></w:tblPr></w:style>
</w:styles>"""

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Default Extension="jpg" ContentType="image/jpeg"/><Default Extension="jpeg" ContentType="image/jpeg"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>"""


def _run(text: str, bold: bool = False, color: Optional[str] = None, size: Optional[int] = None) -> str:
    props = ("<w:b/>" if bold else "") + (f'<w:color w:val="{color}"/>' if color else "") + (f'<w:sz w:val="{size}"/>' if size else "")
    return f'<w:r>{"<w:rPr>" + props + "</w:rPr>" if props else ""}<w:t xml:space="preserve">{escape(str(text))}</w:t></w:r>'


def _para(text: str = "", style: Optional[str] = None, bold: bool = False, runs: Optional[str] = None) -> str:
    return f'<w:p>{"<w:pPr><w:pStyle w:val=" + chr(34) + style + chr(34) + "/></w:pPr>" if style else ""}{runs if runs is not None else _run(text, bold) if text else ""}</w:p>'


def _cell(text: str, width: int, bold: bool = False, shade: Optional[str] = None) -> str:
    fill = f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>' if shade else ""
    return f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{fill}</w:tcPr>{_para(runs=_run(text, bold))}</w:tc>'


def _table(columns: List[Tuple[str, float]], rows: List[list], empty: str = "") -> str:
    total = sum(max(float(w), 0.01) for _, w in columns) or 1.0
    widths = [int(PAGE_W_TW * max(float(w), 0.01) / total) for _, w in columns]
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    head = '<w:tr><w:trPr><w:tblHeader/></w:trPr>' + "".join(_cell(name, w, True, "E8EDF4") for (name, _), w in zip(columns, widths)) + "</w:tr>"
    body = "".join("<w:tr>" + "".join(_cell(str(c), w) for c, w in zip(row, widths)) + "</w:tr>" for row in rows)
    if not rows and empty:
        body = "<w:tr>" + _cell(empty, sum(widths)) + "</w:tr>"
    return f'<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="{sum(widths)}" w:type="dxa"/><w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>{head}{body}</w:tbl>' + _para()


def _kv(rows: List[list]) -> str:
    widths = [int(PAGE_W_TW * 0.3), int(PAGE_W_TW * 0.7)]
    body = "".join("<w:tr>" + _cell(str(k), widths[0], True, "F3F5F8") + _cell(str(v), widths[1]) + "</w:tr>" for k, v in rows)
    return f'<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="{sum(widths)}" w:type="dxa"/><w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid><w:gridCol w:w="{widths[0]}"/><w:gridCol w:w="{widths[1]}"/></w:tblGrid>{body}</w:tbl>' + _para()


def _image_size(path: str, box_w: float, box_h: float) -> Optional[Tuple[int, int]]:
    """EMU size of a logo inside a box in points (proportions kept); None when it cannot be read as an image."""
    from epc_report.core import logo
    im = logo.image(path)                                                                # PNG, JPEG or SVG; an unreadable logo is left out
    if im is None:
        return None
    w, h = im.size
    scale = min(box_w / max(w, 1), box_h / max(h, 1))
    return int(w * scale * EMU_PER_PT), int(h * scale * EMU_PER_PT)


def _picture(rid: str, number: int, cx: int, cy: int) -> str:
    return (f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{number}" name="Logo {number}"/>'
            f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="{number}" name="Logo {number}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')


def _png_bytes(path: str) -> bytes:
    """The logo as the bytes of a PNG (what the Word package carries), whatever file it came from."""
    import io
    from epc_report.core import logo
    out = io.BytesIO()
    logo.image(path).save(out, format="PNG")
    return out.getvalue()


def _cover(rep: dict, images: List[Tuple[str, bytes, str]]) -> str:
    """The first page: the logos (those that can be drawn), the title, the subtitle and the data of the document, then a page break."""
    cover = rep["cover"]
    logos = []
    for path in (cover.get("logos") or [])[:2]:
        size = _image_size(path, 150, 60) if path else None
        if size:
            rid = f"rIdImg{len(images) + 1}"
            images.append((rid, _png_bytes(path), "png"))
            logos.append(_picture(rid, len(images), *size))
    out = _para(runs="".join(r + _run("      ") for r in logos)) if logos else ""
    out += _para() * 6 + _para(rep.get("title", ""), "Title") + _para(rep.get("subtitle", ""), "Subtitle") + _para()
    out += _kv(cover.get("rows") or []) if cover.get("rows") else ""
    return out + '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def _figure(b: dict, images: List[Tuple[str, bytes, str]]) -> str:
    """A figure block as a picture (PNG drawn from its shapes) with its title and caption."""
    from epc_report.core import report_pdf
    data, w, h = report_pdf.figure_png(b)
    rid = f"rIdImg{len(images) + 1}"
    images.append((rid, data, "png"))
    out = _para(b["title"], "Heading1") if b.get("title") else ""
    out += _para(runs=_picture(rid, len(images), int(w * EMU_PER_PT), int(h * EMU_PER_PT)))
    return out + (_para(b["caption"]) if b.get("caption") else "")


def _block(b: dict, images: Optional[List[Tuple[str, bytes, str]]]) -> List[str]:
    """One block of the report as the XML of the document."""
    kind = b.get("type")
    if kind == "bullets":
        return [_para(runs=_run("•  " + str(i))).replace("<w:p>", '<w:p><w:pPr><w:pStyle w:val="ListBullet"/></w:pPr>', 1) for i in b["items"]]
    if kind == "figure":
        return [_figure(b, images)] if images is not None else []
    one = {"h": lambda: _para(b.get("text"), "Heading1"), "p": lambda: _para(b.get("text")), "kv": lambda: _kv(b.get("rows")), "table": lambda: _table(b.get("columns"), b.get("rows"), b.get("empty", ""))}
    return [one[kind]()] if kind in one else []


def _blocks(blocks: List[dict], images: Optional[List[Tuple[str, bytes, str]]] = None) -> str:
    return "".join("".join(_block(b, images)) for b in blocks)


def _footer(rep: dict) -> str:
    label = rep.get("page_label", "{n}/{total}")
    before, _, rest = label.partition("{n}")
    middle, _, after = rest.partition("{total}")
    field = lambda code: f'<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> {code} </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r>'
    runs = _run(str(rep.get("footer", "")) + "    ") + _run(before) + field("PAGE") + _run(middle) + field("NUMPAGES") + _run(after)
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {NS}>{_para(runs=runs, style="Footer")}</w:ftr>'


def render_bytes(rep: dict, date=None) -> bytes:
    """The Word document of a report as bytes; nothing is written. `date` (a datetime) is the time of every entry of the file: given, the same report gives the same bytes."""
    images: List[Tuple[str, bytes, str]] = []
    body = _cover(rep, images) if rep.get("cover") else _para(rep.get("title", ""), "Title") + (_para(rep.get("subtitle", ""), "Subtitle") if rep.get("subtitle") else "")
    body += _blocks(rep.get("blocks") or [], images)
    sect = '<w:sectPr><w:footerReference w:type="default" r:id="rIdFooter"/><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="567" w:footer="567" w:gutter="0"/></w:sectPr>'
    document = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {NS}><w:body>{body}{sect}</w:body></w:document>'
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '<Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>'
            + "".join(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{rid}.{ext}"/>' for rid, _, ext in images) + "</Relationships>")
    import io
    files = [("[Content_Types].xml", CONTENT_TYPES), ("_rels/.rels", ROOT_RELS), ("word/document.xml", document), ("word/styles.xml", STYLES),
             ("word/footer1.xml", _footer(rep)), ("word/_rels/document.xml.rels", rels)] + [(f"word/media/{rid}.{ext}", data) for rid, data, ext in images]
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in files:
            if date is None:
                z.writestr(name, content)                                                   # the clock is the time of every entry (as `render` always did)
            else:
                info = zipfile.ZipInfo(name, date_time=(date.year, date.month, date.day, date.hour, date.minute, date.second))
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, content)
    return out.getvalue()


def render(rep: dict, dst: Path) -> Path:
    """The Word document written to `dst` (a thin caller of `render_bytes`)."""
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    Path(dst).write_bytes(render_bytes(rep))
    return Path(dst)


def main(argv: Optional[list] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print("usage: python -m epc_report.core.report_docx <report.json> <out.docx>", file=sys.stderr)
        return 2
    render(json.loads(Path(args[0]).read_text(encoding="utf-8")), Path(args[1]))
    print("OK", args[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
