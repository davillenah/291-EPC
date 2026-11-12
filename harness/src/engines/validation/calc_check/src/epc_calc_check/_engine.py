"""The only module that touches the calculation engine (`epc_aea90364`). Loaded on first use, so importing `epc_calc_check` reads no data."""
import functools
import inspect
from types import SimpleNamespace


@functools.lru_cache(maxsize=1)
def engine():
    """The engine functions and constants the checks call or compare with."""
    from epc_aea90364 import aea_ampacity, aea_conductors, aea_pipeline, aea_protection, aea_voltage_drop, board_memo, policy, voltage_drop
    return SimpleNamespace(
        AMP=aea_ampacity, CO=aea_conductors, PROT=aea_protection, VD=aea_voltage_drop, VDG=voltage_drop, MEMO=board_memo, policy=policy,
        series_in=tuple(aea_pipeline.SERIE_IN_A), series_icu=tuple(aea_pipeline.SERIE_ICU_KA), series_s=tuple(aea_pipeline.SERIE_S_MM2),
        conductor_temp_c=inspect.signature(aea_pipeline.calculate).parameters["temp_c"].default)
