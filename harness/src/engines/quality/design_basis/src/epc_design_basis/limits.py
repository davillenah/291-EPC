"""The limits the calculation engines will apply, READ from the engines' public accessors.

Nothing here holds a value: every number comes out of a call to the engine that owns it (imported lazily, only to read). The register ids are identifiers of the
norm-register records of those engine values (not values). A limit whose accessor is missing or refuses its arguments becomes an issue.
"""
import importlib
from collections import namedtuple

PENDING = "pending review"
READ_ERRORS = (ImportError, AttributeError, KeyError, ValueError, TypeError)

Spec = namedtuple("Spec", "key label unit module name args kwargs records")

VD_MODULE = "epc_voltage_drop.aea_voltage_drop"
VD_TYPES = ("iluminacion", "tomacorrientes", "seccional", "motor_regimen", "motor_arranque")
VD_RECORDS = ("aea90364.constant.771-19-limites-caida-pct",)
EARTHING_MODULE = "epc_grounding.aea_earthing"
SECTIONAL_RECORDS = ("aea90364.constant.771-18-t-seccional-s",)
SELECTIVITY_RECORDS = ("aea90364.constant.771-18-t-seccional-s", "aea90364.code.aea_earthing.tiempo_seccional_max_s.selectividad")
TABLE_RECORDS = ("aea90364.constant.771-18-iii-tiempos-desconexion-s",)
SC_MODULE = "epc_short_circuit.short_circuit"
C_MIN_RECORDS = ("aea90364.code.aea_pipeline.c_min_bt",)
U0_MODULE = "epc_load_balance.system_voltage"
U0_RECORDS = ("aea90364.code.system_voltage.u0_380", "aea90364.code.board_memo.u0_v")
TABLE_SCHEMES = ("TT", "TN")


def source_of(spec):
    return f"{spec.module}.{spec.name}"


def static_specs():
    """The limits that do not depend on the profile: voltage-drop limits per circuit type, sectional disconnection times, c_min."""
    specs = [Spec(f"voltage_drop_limit.{t}", f"Voltage drop limit, {t}", "%", VD_MODULE, "limite_caida_pct", (t,), {}, VD_RECORDS) for t in VD_TYPES]
    specs += [Spec("disconnection_time.sectional.TT", "Maximum disconnection time, sectional circuits, TT", "s", EARTHING_MODULE, "tiempo_seccional_max_s", ("TT",), {}, SECTIONAL_RECORDS),
              Spec("disconnection_time.sectional.TN", "Maximum disconnection time, sectional circuits, TN", "s", EARTHING_MODULE, "tiempo_seccional_max_s", ("TN",), {}, SECTIONAL_RECORDS),
              Spec("disconnection_time.sectional.TN_selectivity", "Maximum disconnection time, sectional circuits, TN, when selectivity justifies it", "s", EARTHING_MODULE,
                   "tiempo_seccional_max_s", ("TN",), {"selectividad": True}, SELECTIVITY_RECORDS)]
    specs.append(Spec("c_min", "Voltage factor c_min for the minimum short-circuit current, low voltage", None, SC_MODULE, "C_MIN_BT", None, {}, C_MIN_RECORDS))
    return specs


def u0_spec(line_voltage):
    return Spec("system_voltage_to_earth", "Phase-to-earth voltage U0 of the declared system", "V", U0_MODULE, "system_u0", (line_voltage,), {}, U0_RECORDS)


def table_spec(scheme, u0):
    return Spec(f"disconnection_time.table.{scheme}", f"Maximum disconnection time by voltage, {scheme}, alternating current", "s", EARTHING_MODULE,
                "tiempo_desconexion_max_s", (scheme, u0), {}, TABLE_RECORDS)


def read(spec):
    """(value, None) from the engine accessor, or (None, issue text) when it cannot be read."""
    try:
        accessor = getattr(importlib.import_module(spec.module), spec.name)
        value = accessor if spec.args is None else accessor(*spec.args, **spec.kwargs)
    except READ_ERRORS as exc:
        return None, f"{spec.key}: cannot be read from {source_of(spec)}: {exc}"
    return value, None


def review_status(records, norm_status):
    """`rejected` if any record is rejected; `verified` only if every record is verified; otherwise `pending review` (also for a record the caller does not know)."""
    states = [(norm_status or {}).get(r, PENDING) for r in records]
    if "rejected" in states:
        return "rejected"
    return "verified" if states and all(s == "verified" for s in states) else PENDING


def _item(spec, value, norm_status):
    return {"key": spec.key, "label": spec.label, "value": value, "unit": spec.unit, "source": source_of(spec), "review_status": review_status(spec.records, norm_status)}


class Collected:
    """Items, issues and register ids of the limits read, in the order they were read."""

    def __init__(self, norm_status):
        self.norm_status, self.items, self.issues, self.records, self.values = norm_status, [], [], [], {}

    def add(self, spec):
        value, issue = read(spec)
        if issue:
            self.issues.append(issue)
            return None
        self.items.append(_item(spec, value, self.norm_status))
        self.records.extend(r for r in spec.records if r not in self.records)
        self.values[spec.key] = value
        return value


def _line_voltage(supply):
    voltage = supply.get("voltage") or {}
    if voltage.get("value") is None or voltage.get("unit") != "V":
        return None
    return voltage["value"]


def _voltage_dependent(collected, supply):
    line = _line_voltage(supply)
    if line is None:
        collected.issues.append("system_voltage_to_earth: supply.voltage with a value in V is missing in the profile; U0 cannot be read")
        return None
    return collected.add(u0_spec(line))


def _scheme_table(collected, scheme, u0):
    if scheme not in TABLE_SCHEMES:
        collected.issues.append(f"disconnection_time.table: no disconnection time is read for the earthing system {scheme!r}")
    elif u0 is None:
        collected.issues.append(f"disconnection_time.table.{scheme}: needs U0, which could not be read")
    else:
        collected.add(table_spec(scheme, u0))


def read_limits(supply, norm_status=None):
    """Collected limits for the declared supply: (items, issues, register ids of the values read)."""
    collected = Collected(norm_status)
    for spec in static_specs():
        collected.add(spec)
    u0 = _voltage_dependent(collected, supply)
    _scheme_table(collected, supply.get("earthing_system"), u0)
    return collected.items, collected.issues, collected.records
