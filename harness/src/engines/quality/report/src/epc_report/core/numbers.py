"""Numbers in the text of a report, written the way the reader of the language writes them (PV-16).

`localize(report, lang)` returns a copy of the report whose text shows long decimals rounded to two places and groups the thousands: English `47,983.54`, Spanish `47.983,54`. It changes how a number is
written, never its value: the `facts` that the audit compares are left as they are. Codes (`C-05`, `SIM02-PV`, `TR-001`), versions (`0.1.0`) and dates (`2026-11-27`) are not numbers here and stay as written.
"""
import re

DECIMALS = 2
SEPARATORS = {"en": (",", "."), "es": (".", ",")}       # (thousands, decimal)
_NUMBER = re.compile(r"\d{4}-\d{2}-\d{2}|(?<![\w.,])(\d+)(?:\.(\d+))?(?![\w]|\.\d)")


def _write(match, lang):
    whole, frac = match.group(1), match.group(2)
    if whole is None:
        return match.group(0)                              # a date
    if len(whole) > 1 and whole.startswith("0"):
        return match.group(0)                              # a code such as 001 or 05
    thousands, decimal = SEPARATORS.get(lang, SEPARATORS["en"])
    if frac is not None and len(frac) > DECIMALS:
        rounded = f"{float(match.group(0)):.{DECIMALS}f}".rstrip("0").rstrip(".")
        whole, _, frac = rounded.partition(".")
        frac = frac or None
    text = f"{int(whole):,}".replace(",", thousands) if len(whole) > 4 else whole
    return text + (decimal + frac if frac is not None else "")


def text(value, lang):
    """One string with its numbers written for `lang`."""
    return _NUMBER.sub(lambda m: _write(m, lang), value)


def _walk(value, lang):
    if isinstance(value, str):
        return text(value, lang)
    if isinstance(value, (list, tuple)):
        return type(value)(_walk(v, lang) for v in value)
    if isinstance(value, dict):
        return {k: _walk(v, lang) for k, v in value.items()}
    return value


def localize(report, lang):
    """The report with the numbers of its text written for `lang` (title, subtitle, footer and every block except figures)."""
    out = dict(report)
    for key in ("title", "subtitle", "footer"):
        if isinstance(out.get(key), str):
            out[key] = text(out[key], lang)
    out["blocks"] = [b if b.get("type") == "figure" else _walk(b, lang) for b in report["blocks"]]
    return out
