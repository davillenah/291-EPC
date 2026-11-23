"""Transformer sizing: pure functions, no I/O (the rating series is read lazily by `ratings`)."""
import math

from epc_short_circuit.short_circuit import corriente_asignada_trafo

from epc_transformer_sizing import ratings
from epc_transformer_sizing.errors import TransformerSizingError

NO_PARALLEL = "no single unit; paralleling not modelled"
PENDING = "pending review: values to be verified by the owner against the supply authority / manufacturer catalog"


def _check(value, name, minimum=0.0, strict=True):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise TransformerSizingError("err_not_finite_number", name=name, value=value)
    if (strict and value <= minimum) or (not strict and value < minimum):
        raise TransformerSizingError("err_out_of_range", name=name, relation='>' if strict else '>=', minimum=minimum, got=value)


def rated_current_a(sn_kva, un_v):
    """Rated current In [A] = Sn / (sqrt(3) * Un), for Sn in kVA and Un in V (line voltage)."""
    _check(sn_kva, "sn_kva")
    _check(un_v, "un_v")
    return corriente_asignada_trafo(sn_kva * 1000.0, un_v)


def apparent_power_kva(i_a, un_v):
    """S [kVA] = sqrt(3) * Un * I / 1000 of a three-phase load of `i_a` amperes at line voltage `un_v` (V): the demand a board head current represents."""
    _check(i_a, "i_a")
    _check(un_v, "un_v")
    return math.sqrt(3.0) * un_v * i_a / 1000.0


def required_apparent_power_kva(demand_kva, reserve_pct):
    """Demand x (1 + reserve / 100). `reserve_pct` is required: no growth or reserve criterion has been decided."""
    if reserve_pct is None:
        raise TransformerSizingError("err_reserve_required")
    _check(demand_kva, "demand_kva")
    _check(reserve_pct, "reserve_pct", strict=False)
    return demand_kva * (1.0 + reserve_pct / 100.0)


def _series_of(series):
    values = tuple(sorted(series)) if series is not None else ratings.standard_ratings_kva()
    if not values:
        raise TransformerSizingError("err_series_empty")
    return values


def select_rating(required_kva, series=None):
    """The smallest rating of the series that is >= `required_kva` (the series defaults to the data file)."""
    _check(required_kva, "required_kva")
    values = _series_of(series)
    for rating in values:
        if rating >= required_kva:
            return rating
    raise TransformerSizingError("err_above_largest_rating", required_kva=required_kva, largest=values[-1], note=NO_PARALLEL)


def loading_pct(demand_kva, rating_kva):
    """Demand as a percentage of the rating."""
    _check(demand_kva, "demand_kva")
    _check(rating_kva, "rating_kva")
    return demand_kva / rating_kva * 100.0


def _assumptions(reserve_pct, custom_series):
    source = "rating series given by the caller" if custom_series else f"standard rating series from the data file, {PENDING}"
    return [f"reserve of {reserve_pct:g} % given by the caller (no reserve criterion decided)", source,
            "impedance (uk %), losses and short-circuit contribution not modelled", "single unit; paralleling not modelled"]


def size_transformer(demand_kva, un_secondary_v, reserve_pct, series=None):
    """Size one transformer: rating, loading and rated secondary current, with the assumptions and the norm records relied on."""
    required = required_apparent_power_kva(demand_kva, reserve_pct)
    rating = select_rating(required, series)
    return {"rating_kva": rating, "required_kva": required, "loading_pct": loading_pct(demand_kva, rating),
            "rated_current_a": rated_current_a(rating, un_secondary_v), "series_used": list(_series_of(series)),
            "assumptions": _assumptions(reserve_pct, series is not None),
            "norm_records": [] if series is not None else [ratings.RECORD_ID]}
