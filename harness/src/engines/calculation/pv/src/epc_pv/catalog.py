"""Equipment catalog helpers: the inverter the harness proposes when the person names none, and the short-circuit current assumption when a data sheet lacks it.

Nothing here invents manufacturer data. The inverters are the extracted catalog records (`data/inverter_catalog.json`, pending review). The pick is the model whose unit count gives a DC/AC ratio
closest to the requested one (fewest units on a tie). A data sheet gap (`isc_max_input_a` null) is left null: the engine checks the operating input current only and says so (`isc_not_checked`); nothing is invented.
"""
import json
from pathlib import Path
from typing import Any, Dict, List

from epc_pv.strings import half_up

AUTO = "auto"
_DATA = Path(__file__).parent / "data"


def inverters() -> List[Dict[str, Any]]:
    return json.loads((_DATA / "inverter_catalog.json").read_text(encoding="utf-8"))["inverters"]


def with_isc(record: Dict[str, Any], given: Any = None) -> Dict[str, Any]:
    """The inverter block with the short-circuit limit the person gave, or the data sheet's (null when the sheet has none)."""
    block = dict(record["inverter"])
    if given is not None:
        block["isc_max_input_a"] = float(given)
    return block


def pick_inverter(n_modules: int, pmax_w: float, dc_ac_ratio: float) -> Dict[str, Any]:
    """The catalog record whose count (as `strings.inverter_count` would give it) is closest to `dc_ac_ratio`; fewest units on a tie."""
    dc_w = n_modules * pmax_w

    def score(rec: Dict[str, Any]):
        pac = float(rec["inverter"]["pac0_w"])
        n = max(1, half_up(dc_w / (dc_ac_ratio * pac)))
        return (abs(dc_w / (n * pac) - dc_ac_ratio), n, pac)

    return min(inverters(), key=score)
