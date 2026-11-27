"""A logo as a raster image for the PDF and Word covers: PNG and JPEG are opened as they are; an SVG is drawn here (filled and stroked shapes, with the colours it gives; gradients, text and filters are left out), because
the PDF and Word writers take pictures, not vector files. `image(path)` gives a PIL image on a transparent background, or None when the file cannot be read as a logo."""
from pathlib import Path
from typing import List, Optional, Tuple

RASTER = (".png", ".jpg", ".jpeg")
SIDE = 4                                                  # the logo is drawn at 4 times the size it will have (anti-aliasing) and reduced
MAX_PX = 800                                              # the longest side of the picture made from an SVG
CURVE_STEPS = 16
Point = Tuple[float, float]


def _rgba(color, opacity: float = 1.0) -> Optional[Tuple[int, int, int, int]]:
    """A colour of the SVG as an RGBA tuple; None when there is none ('none', a gradient reference...)."""
    if color is None or getattr(color, "value", None) is None:
        return None
    try:
        return (int(color.red), int(color.green), int(color.blue), int(round(255 * float(opacity) * (color.alpha / 255.0 if color.alpha is not None else 1.0))))
    except (TypeError, ValueError, AttributeError):
        return None


def _segment_points(seg) -> List[Point]:
    """The points of a segment: its end for a straight line, a few along it for a curve."""
    steps = 1 if seg.__class__.__name__ == "Line" else CURVE_STEPS
    return [(float(p.x), float(p.y)) for p in (seg.point(i / steps) for i in range(1, steps + 1))]


def _subpaths(shape) -> List[List[Point]]:
    """The outlines of a shape as lists of points, curves cut into short straight pieces."""
    from svgelements import Close, Move, Path as SvgPath
    path = shape if isinstance(shape, SvgPath) else SvgPath(shape.segments())
    out: List[List[Point]] = []
    current: List[Point] = []
    for seg in path:
        if isinstance(seg, Move):
            out += [current] if len(current) > 1 else []
            current = [(float(seg.end.x), float(seg.end.y))]
        elif isinstance(seg, Close):
            current += current[:1]
        elif seg.end is not None:
            current += _segment_points(seg)
    return out + ([current] if len(current) > 1 else [])


def _fill_mask(subs: List[List[Point]], size: Tuple[int, int]):
    """The mask of the filled area of a shape: every closed outline filled, an outline inside another one makes a hole (even-odd)."""
    from PIL import Image, ImageChops, ImageDraw
    mask = Image.new("L", size, 0)
    for sub in (s for s in subs if len(s) > 2):
        piece = Image.new("L", size, 0)
        ImageDraw.Draw(piece).polygon(sub, fill=255)
        mask = ImageChops.difference(mask, piece)
    return mask


def _opacity(shape, name: str) -> float:
    return float(getattr(shape, name, None) or 1.0)


def _stroke(canvas, shape, subs: List[List[Point]], scale: float) -> None:
    """The lines of a shape that has a stroke colour, with the width it gives."""
    from PIL import ImageDraw
    color = _rgba(shape.stroke, _opacity(shape, "stroke_opacity"))
    if not color:
        return
    width = max(1, int(round(float(getattr(shape, "stroke_width", None) or 1.0) * scale)))
    draw = ImageDraw.Draw(canvas)
    for sub in (s for s in subs if len(s) > 1):
        draw.line(sub, fill=color, width=width)


def _draw_shape(canvas, shape, scale: float, origin: Point) -> None:
    from PIL import Image
    subs = [[((x - origin[0]) * scale, (y - origin[1]) * scale) for x, y in sub] for sub in _subpaths(shape)]
    fill = _rgba(shape.fill, _opacity(shape, "fill_opacity"))
    if fill:
        canvas.paste(Image.new("RGBA", canvas.size, fill), (0, 0), _fill_mask(subs, canvas.size))
    _stroke(canvas, shape, subs, scale)


def _shapes(source) -> list:
    """The shapes of an SVG given as a file path or as bytes."""
    import io
    from svgelements import SVG, Shape, Text
    parsed = SVG.parse(io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else str(source), reify=True)
    return [e for e in parsed.elements() if isinstance(e, Shape) and not isinstance(e, Text)]


def _extent(shapes: list) -> Optional[Tuple[float, float, float, float]]:
    """The outline of everything drawn (not the one the file declares)."""
    boxes = [b for b in (shape.bbox() for shape in shapes) if b is not None]
    if not boxes:
        return None
    return min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)


def from_svg(path):
    """The SVG (a file path or its bytes) as a PIL image, or None."""
    try:
        from PIL import Image
        shapes = _shapes(path)
        extent = _extent(shapes)
        if not extent:
            return None
        x0, y0, x1, y1 = extent
        scale = MAX_PX * SIDE / max(x1 - x0, y1 - y0, 1e-6)
        canvas = Image.new("RGBA", (int((x1 - x0) * scale) + 1, int((y1 - y0) * scale) + 1), (255, 255, 255, 0))
        for shape in shapes:
            _draw_shape(canvas, shape, scale, (x0, y0))
        return canvas.resize((max(1, canvas.width // SIDE), max(1, canvas.height // SIDE)), Image.LANCZOS)
    except Exception:                                                                    # noqa: BLE001 - a logo that cannot be drawn is left out, never a failed report
        return None


def data_of(logo) -> Optional[bytes]:
    """The bytes of a logo given as data: bytes, or `{"data": bytes}`; None for a path or anything else."""
    if isinstance(logo, (bytes, bytearray)):
        return bytes(logo)
    if isinstance(logo, dict) and isinstance(logo.get("data"), (bytes, bytearray)):
        return bytes(logo["data"])
    return None


def _is_svg(data: bytes) -> bool:
    return b"<svg" in data[:2048].lower() or data.lstrip()[:5].lower() == b"<?xml"


def _from_data(data: bytes):
    """A logo that arrives as bytes (PNG, JPEG or SVG) as a PIL image, or None."""
    if _is_svg(data):
        return from_svg(data)
    try:
        import io
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im:
            return im.convert("RGBA")
    except (OSError, ValueError):
        return None


def image(path) -> Optional[object]:
    """A logo as a PIL image (RGBA), or None when it is missing or cannot be read. `path` is a file path (as before) or the logo as data (bytes or `{"data": bytes}`): a report
    that is called with the logos as data reads no file (ADR-0043)."""
    data = data_of(path)
    if data is not None:
        return _from_data(data)
    if not path or not Path(path).is_file():
        return None
    suffix = Path(path).suffix.lower()
    if suffix == ".svg":
        return from_svg(Path(path))
    if suffix not in RASTER:
        return None
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.convert("RGBA")
    except (OSError, ValueError):                       # a file Pillow cannot identify or decode is left out, as a missing logo (COD-11)
        return None
