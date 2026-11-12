"""Small helpers shared by the checks: number tests, JSON-safe values and the dotted-name lookups."""
import math

HEX64 = "0123456789abcdef"


def is_number(x):
    """A real number: int or float, not a bool, finite."""
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def num(x):
    """`x` when it is a finite real number (bool excluded), else None."""
    return x if is_number(x) else None


def is_sha256(x):
    return isinstance(x, str) and len(x) == 64 and all(c in HEX64 for c in x)


def safe(value, depth=0):
    """The value as JSON can hold it: NaN and infinities become the strings 'nan' / 'inf' / '-inf'; unknown objects their repr."""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if depth > 4:
        return repr(value)[:80]
    if isinstance(value, dict):
        return {str(k): safe(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(v, depth + 1) for v in value]
    return repr(value)[:80]


def walk(value, path=""):
    """(path, leaf) of every leaf of a nested dict/list; paths look like `circuits/3/ib_a`."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield from walk(item, f"{path}/{key}" if path else str(key))
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            yield from walk(item, f"{path}/{i}" if path else str(i))
    else:
        yield path, value
