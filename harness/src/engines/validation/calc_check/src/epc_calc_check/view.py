"""A read-only view of a pipeline result (the JSON form of the discipline `RunResult`) with the stage shapes the checks rely on.

The package does not import the discipline: the stage numbers, names and keys below are the contract of the stage outputs as data. A stage whose status
is not `ok` has no outputs for the checks (`outputs()` returns {}).
"""
import hashlib

from epc_calc_check._values import num

STAGE_SLUGS = {
    1: "intake", 2: "requirements", 3: "input_verification", 4: "load_schedule", 5: "demand", 6: "supply_transformer", 7: "board_structure",
    8: "feeder_sizing", 9: "voltage_drop", 10: "short_circuit", 11: "protection_selectivity", 12: "earthing", 13: "calc_check", 14: "drawings",
    15: "documents", 16: "package_issue"}
STATUSES = ("ok", "not_available", "blocked", "failed")

# keys of `outputs` that an `ok` stage must return
REQUIRED_OUTPUTS = {
    1: ("profile", "inputs_manifest", "loads"), 2: ("design_basis",), 3: ("verified", "manifest_sha256"), 4: ("circuits", "pending"), 5: ("circuits", "pending"),
    7: ("circuits", "board", "supply", "differential_groups_added", "contract_check"), 8: ("circuits", "engine_warnings"), 9: ("circuits", "limits_pct"),
    10: ("circuits", "busbar_icc_ka"), 11: ("circuits", "selectivity", "selectivity_summary", "pending"),
    12: ("circuits", "earthing_system", "rcd_ma", "pending"), 14: ("directory", "files", "summary"), 15: ("documents", "memo_summary", "pending_documents"),
    16: ("revision", "manifests", "transmittal")}
# keys of every circuit row of the circuit stages
ROW_FIELDS = {
    4: ("circuit", "load_id", "ib_a", "p_kw", "phases", "fp", "parent"),
    5: ("circuit", "load_id", "kind", "system", "demand_factor"),
    7: ("circuit", "load_id", "type", "parent", "device_kind", "topology", "device", "chain", "solution"),
    8: ("circuit", "load_id", "in_a", "ib_a", "s_mm2", "s_internal_mm2", "iz_a", "min_section_mm2", "material", "insulation", "method", "route",
        "route_limiting", "pe_mm2", "neutral_mm2", "transition", "i2_a", "overload_ok", "coordination_ok", "compliant"),
    9: ("circuit", "load_id", "length_m", "limit_pct", "own_pct", "accumulated_pct", "du_pct", "compliant"),
    10: ("circuit", "load_id", "icu_ka", "icc_a", "icc_min_a", "breaking_ok", "trip_ok", "k_min", "k_max"),
    11: ("circuit", "load_id", "device", "device_kind", "curve", "in_a", "overload_ok", "coordination_ok", "protection_ok"),
    12: ("circuit", "load_id", "differential", "differential_ok")}
NUMERIC_FIELDS = {
    4: ("ib_a", "p_kw", "phases", "fp"), 5: ("demand_factor",),
    8: ("in_a", "ib_a", "s_mm2", "s_internal_mm2", "iz_a", "min_section_mm2", "pe_mm2", "neutral_mm2", "i2_a"),
    9: ("length_m", "limit_pct", "own_pct", "accumulated_pct", "du_pct"), 10: ("icu_ka", "icc_a", "icc_min_a", "k_min", "k_max"), 11: ("in_a",)}
NULLABLE_FIELDS = ("s_internal_mm2", "iz_a", "icc_min_a", "pe_mm2", "neutral_mm2", "min_section_mm2")
FLAG_FIELDS = {8: ("transition", "overload_ok", "coordination_ok", "compliant"), 9: ("compliant",), 10: ("breaking_ok", "trip_ok"),
               11: ("overload_ok", "coordination_ok", "protection_ok"), 12: ("differential_ok",)}
CIRCUIT_STAGES = (4, 5, 7, 8, 9, 10, 11, 12)


def sha256_of(data):
    """SHA-256 of bytes, or the value itself when it already is a 64-hex string (what `files` may hold)."""
    return hashlib.sha256(data).hexdigest() if isinstance(data, (bytes, bytearray)) else data


class RunView:
    """`results` by stage number, circuit rows by tag, and the optional `project` data and `files` of the caller."""

    def __init__(self, run_result, project=None, files=None, renumbered=False):
        self.renumbered = bool(renumbered)  # finding ids are already unique across the run (the form the pipeline returns), not per stage
        self.run = run_result if isinstance(run_result, dict) else {}
        self.project = project if isinstance(project, dict) else {}
        self.files = files if isinstance(files, dict) else {}
        listed = self.run.get("results")
        self.listed = [r for r in listed if isinstance(r, dict)] if isinstance(listed, list) else []
        self.results = {r["stage"]: r for r in self.listed if isinstance(r.get("stage"), int) and not isinstance(r.get("stage"), bool)}

    def outputs(self, number):
        res = self.results.get(number)
        out = res.get("outputs") if res and res.get("status") == "ok" else None
        return out if isinstance(out, dict) else {}

    def rows(self, number):
        rows = self.outputs(number).get("circuits")
        return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []

    def row(self, number, tag):
        return next((r for r in self.rows(number) if r.get("circuit") == tag), None)

    def tags(self):
        """Circuit tags in the order of the first circuit stage that lists them, without repeats."""
        seen = []
        for number in CIRCUIT_STAGES:
            seen += [r.get("circuit") for r in self.rows(number) if isinstance(r.get("circuit"), str)]
        return list(dict.fromkeys(seen))

    def slug(self, number):
        return STAGE_SLUGS.get(number, f"stage_{number}")

    def value(self, number, tag, key):
        row = self.row(number, tag)
        return row.get(key) if row else None

    def number(self, number, tag, key):
        return num(self.value(number, tag, key))

    def circuit_inputs(self, tag):
        """The engine inputs the caller declared for a circuit (`project["circuits"][tag]`), or None when it did not declare them."""
        entry = (self.project.get("circuits") or {}).get(tag)
        return entry if isinstance(entry, dict) else None
