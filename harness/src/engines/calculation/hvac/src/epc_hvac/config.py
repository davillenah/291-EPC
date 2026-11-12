"""Version and the data the engine reads: the typical values of the method (heat of people, infiltration, solar irradiance, ventilation rates), which the owner confirms on the norms page."""
import json
from functools import lru_cache
from pathlib import Path

VERSION = "0.1.0"
SCHEMA_VERSION = "1.0"
HERE = Path(__file__).resolve().parent
TYPICAL = HERE / "data" / "typical.json"                 # {section: {key: value}}: the file the norms page edits

AIR_SENSIBLE_W_PER_LS_K = 1.23                           # sensible heat of standard air (W per L/s per K)
AIR_LATENT_W_PER_LS_KGKG = 3010.0                        # latent heat of standard air (W per L/s per kg water / kg dry air)
WATTS_PER_REFRIGERATION_TON = 3516.85


@lru_cache(maxsize=None)
def typical() -> dict:
    return json.loads(TYPICAL.read_text(encoding="utf-8"))


def clear_cache() -> None:
    """Read the typical values again (the norms page changed one)."""
    typical.cache_clear()


def params() -> dict:
    return typical()["params"]


def solar_peak_w_m2() -> dict:
    return typical()["solar"]


def ventilation_rates(use: str) -> dict:
    """Outdoor air rates of a use (`default` when the use is not listed)."""
    uses = typical()["ventilation"]
    return uses.get(use, uses["default"])
