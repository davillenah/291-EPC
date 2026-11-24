"""The copies of an array: each item is `{index, row, col, point, rotation}` (rotation in degrees, counter-clockwise).

Rectangular: `rows` by `cols` copies of a base point; the columns run along the direction `angle` and the rows along `angle + 90`; the spacings are signed (a
negative one goes the other way). Polar: `count` copies of a base point turned about a centre; with a fill of 360 degrees the copies are evenly spread round the
whole circle, otherwise the first is at the start and the last at the end of the fill. `rotate_items` turns each copy with its position.
`max_items` has no default: the size a project accepts is its choice.
"""
import math

from epc_arrays.errors import ArraysError


def _number(value, name):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ArraysError("err_not_number", name=name, value=value)
    return float(value)


def _point(value, name):
    if not isinstance(value, (list, tuple)) or len(value) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in value):
        raise ArraysError("err_not_point", name=name, value=value)
    return (float(value[0]), float(value[1]))


def _count(value, name, low=1):
    if isinstance(value, bool) or not isinstance(value, int) or value < low:
        raise ArraysError("err_not_count", name=name, low=low, value=value)
    return value


def _limit(count, max_items):
    limit = _count(max_items, "max_items")
    if count > limit:
        raise ArraysError("err_too_many", count=count, limit=limit)


def _clean(x):
    return round(x, 9) + 0.0


def rectangular(base, rows, cols, row_spacing, col_spacing, *, angle_deg, max_items):
    """`rows * cols` items, row by row from the base point."""
    base, rows, cols = _point(base, "base"), _count(rows, "rows"), _count(cols, "cols")
    dr, dc, angle = _number(row_spacing, "row_spacing"), _number(col_spacing, "col_spacing"), _number(angle_deg, "angle_deg")
    _limit(rows * cols, max_items)
    if rows > 1 and dr == 0:
        raise ArraysError("err_zero_spacing", name="row_spacing", what="row")
    if cols > 1 and dc == 0:
        raise ArraysError("err_zero_spacing", name="col_spacing", what="column")
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    items = []
    for row in range(rows):
        for col in range(cols):
            x, y = col * dc, row * dr
            items.append({"index": len(items), "row": row, "col": col, "rotation": _clean(angle),
                          "point": [_clean(base[0] + x * c - y * s), _clean(base[1] + x * s + y * c)]})
    return items


def _step(fill, count):
    if fill == 0:
        raise ArraysError("err_fill_zero")
    if abs(fill) > 360:
        raise ArraysError("err_fill_range", value=fill)
    if count == 1:
        return 0.0
    return fill / count if abs(fill) == 360 else fill / (count - 1)


def polar(center, base, count, fill_deg, *, rotate_items, max_items):
    """`count` items; the first is at the base point."""
    center, base, count = _point(center, "center"), _point(base, "base"), _count(count, "count")
    fill = _number(fill_deg, "fill_deg")
    _limit(count, max_items)
    step = _step(fill, count)
    radius_x, radius_y = base[0] - center[0], base[1] - center[1]
    items = []
    for n in range(count):
        a = math.radians(n * step)
        c, s = math.cos(a), math.sin(a)
        items.append({"index": n, "row": 0, "col": n, "rotation": _clean(n * step) if rotate_items else 0.0,
                      "point": [_clean(center[0] + radius_x * c - radius_y * s), _clean(center[1] + radius_x * s + radius_y * c)]})
    return items
