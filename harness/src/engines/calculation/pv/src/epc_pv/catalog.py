"""Equipment catalog helpers: the inverter the harness proposes when the person names none, and the short-circuit current assumption when a data sheet lacks it.

Nothing here invents manufacturer data. The inverters are derived from the inverter data sheets of `data/pv_inverters/inverters` (`equipment.inverters()`, pending review): that is the only source (ADR-0012); `data/inverter_catalog.json` is no longer read. The pick is the model whose unit count gives a DC/AC ratio
closest to the requested one (fewest units on a tie). A data sheet gap (`isc_max_input_a` null) is left null: the engine checks the operating input current only and says so (`isc_not_checked`); nothing is invented.
"""
import json
from pathlib import Path
from typing import Any, Dict, List

from epc_pv import equipment
from epc_pv.model import PvError
from epc_pv.strings import half_up

AUTO = "auto"
_DATA = Path(__file__).parent / "data"


def inverters() -> List[Dict[str, Any]]:
    return equipment.inverters()


def module_records() -> List[Dict[str, Any]]:
    """Every module of the product catalog (electrical data, pending review)."""
    return json.loads((_DATA / "module_catalog.json").read_text(encoding="utf-8"))["modules"]


def with_isc(record: Dict[str, Any], given: Any = None) -> Dict[str, Any]:
    """The inverter block with the short-circuit limit the person gave, or the data sheet's (null when the sheet has none)."""
    block = dict(record["inverter"])
    if given is not None:
        block["isc_max_input_a"] = float(given)
    return block


def pick_inverter(n_modules: int, pmax_w: float, dc_ac_ratio: float, module: Dict[str, Any] = None, t_min_c: float = None, t_cell_max_c: float = None) -> Dict[str, Any]:
    """The catalog record whose count (as `strings.inverter_count` would give it) is closest to `dc_ac_ratio` (to two decimals); fewest units on a tie.
    With the `module` block (and the design temperatures, else the STC voltages), only inverters that admit a string of that module are candidates (`strings.series_range`)."""
    dc_w = n_modules * pmax_w
    pool = inverters()
    if module is not None:
        from epc_pv.strings import series_range
        cold, hot = (25.0, 25.0) if t_min_c is None or t_cell_max_c is None else (t_min_c, t_cell_max_c)      # without the design temperatures: the STC voltages (a necessary condition only)
        fits = [r for r in pool if (lambda g: g["s_min"] <= g["s_max"])(series_range(module, r["inverter"], cold, hot))]
        pool = fits or pool
        carries = [r for r in pool if int(r["inverter"]["i_max_input_a"] // float(module["imp_a"])) >= 1]      # an input that admits no string of the module is never picked
        pool = carries or pool

    cold, hot = (25.0, 25.0) if t_min_c is None or t_cell_max_c is None else (t_min_c, t_cell_max_c)

    def count(rec: Dict[str, Any]) -> int:
        """The inverters this record would really need: the ratio count, raised when the strings of the array overload its MPPT inputs (the rule `feasibility.add_inverters_for_current` applies later)."""
        pac = float(rec["inverter"]["pac0_w"])
        by_ratio = max(1, half_up(dc_w / (dc_ac_ratio * pac)))
        if module is None:
            return by_ratio
        from epc_pv import config, strings
        try:
            lay = strings.layout({"id": "pick", "n_modules": n_modules, "module": module, "inverter": rec["inverter"], "n_inverters": by_ratio}, cold, hot, config.params()["strings"])
        except PvError:
            return by_ratio
        limit = lay["strings_per_mppt_limit"]
        if lay["strings_per_mppt"] > limit > 0:
            return max(by_ratio, -(-lay["strings"] // (int(rec["inverter"]["n_mppt"]) * limit)))
        return by_ratio

    def score(rec: Dict[str, Any]):
        pac, n = float(rec["inverter"]["pac0_w"]), count(rec)
        return (round(abs(dc_w / (n * pac) - dc_ac_ratio), 2), n, pac)

    return min(pool, key=score)
