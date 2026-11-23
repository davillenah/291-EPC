"""Conservative rounding of the TT earth resistance Ra (decision D11): two decimals, never an integer.

A maximum allowed Ra rounds DOWN, so the rounded limit never exceeds the exact one. A measured or computed Ra compared with the limit rounds UP,
so the rounded value is never optimistic. Decimal arithmetic avoids float errors (0.29 stays 0.29, 12.6 stays 12.60); the float noise of a
computed quotient (40.00000000000001) is removed first, at nine decimals, so it can never move a value to the next cent.
"""
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR

_CENT = Decimal("0.01")
_NOISE = Decimal("0.000000001")


def _round_2(x: float, mode: str) -> float:
    exact = Decimal(repr(float(x))).quantize(_NOISE)
    return float(exact.quantize(_CENT, rounding=mode))


def round_down_2(x: float) -> float:
    """Floor to two decimals: for a maximum allowed Ra [Ω]."""
    return _round_2(x, ROUND_FLOOR)


def round_up_2(x: float) -> float:
    """Ceiling to two decimals: for a measured or computed Ra [Ω] compared with the limit."""
    return _round_2(x, ROUND_CEILING)
