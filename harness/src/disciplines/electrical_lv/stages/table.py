"""The PRD section 12 table (12 stages) as a fixed ordered tuple. Titles, engines and status words are copied from the PRD.

A test parses the PRD table and compares it with this one, so code and PRD cannot drift.
"""
from collections import namedtuple

StageSpec = namedtuple("StageSpec", "number slug title engines_text engines status_text phase1_status")


def _spec(number, slug, title, engines_text, engines, status_text):
    word = "implemented" if status_text.startswith("implemented") else status_text
    phase1 = word if word in ("implemented", "in development", "planned") else "in development"  # "in part"
    return StageSpec(number, slug, title, engines_text, tuple(engines), status_text, phase1)


STAGE_TABLE = (
    _spec(1, "intake", "Intake: profile, inputs, hashes", "platform", [("platform", None)], "in development"),
    _spec(2, "requirements_inputs", "Requirements and design basis (criteria, profile, assumptions) and input verification (plans vs loads vs requirements)",
          "quality (design basis), cad/plan, validation", [("quality", "design_basis"), ("cad", "plan"), ("validation", None)], "in development"),
    _spec(3, "loads_demand", "Load schedule, phase balance, demand and simultaneity (771.9)", "calculation/load_balance",
          [("calculation", "load_balance")], "implemented"),
    _spec(4, "supply_transformer", "Supply and transformer sizing", "calculation/transformer_sizing",
          [("calculation", "transformer_sizing")], "planned"),
    _spec(5, "board_structure", "Board structure and circuit assignment", "calculation, validation",
          [("calculation", None), ("validation", None)], "implemented"),
    _spec(6, "cable_sizing", "Cable and protection sizing: feeder and circuit section (Ib ≤ In ≤ Iz, I2 ≤ 1.45 Iz, installation method), accumulated voltage drop (D17), "
          "short-circuit currents (max/min), protection device", "calculation/feeder_sizing, voltage_drop, short_circuit",
          [("calculation", "feeder_sizing"), ("calculation", "voltage_drop"), ("calculation", "short_circuit")], "implemented"),
    _spec(7, "selectivity", "Protection selectivity and coordination study", "calculation/selectivity",
          [("calculation", "selectivity")], "implemented"),
    _spec(8, "earthing", "Earthing and fault protection (TT: Ra; TN: Zs = c_min·U0/Ia; disconnection times)",
          "calculation/grounding", [("calculation", "grounding")], "implemented"),
    _spec(9, "calc_check", "Deterministic verification (calc_check): recalculation, format, cross-document consistency",
          "validation", [("validation", None)], "in development"),
    _spec(10, "drawings", "Drawings: SLD, board layouts", "cad", [("cad", None)], "implemented (SLD)"),
    _spec(11, "documents", "Documents and lists: calculation report, specification, cable list, terminal-block list, BOQ, datasheets, RFQ, descriptive report",
          "quality, procurement", [("quality", None), ("procurement", None)], "in part"),
    _spec(12, "package_issue", "Package issue: manifests, review status, transmittal", "platform", [("platform", None)], "planned"),
)

# The slices that a grouped stage runs (the stage output holds one section per slice, named by its slug). A slice keeps its number of the former
# 16-stage table, which is the vocabulary of `epc_calc_check` and of the PENDING_ITEMS: slice number -> (slug, number of the stage that groups it).
SLICES = {2: ("requirements", 2), 3: ("input_verification", 2), 4: ("load_schedule", 3), 5: ("demand", 3),
          8: ("feeder_sizing", 6), 9: ("voltage_drop", 6), 10: ("short_circuit", 6), 11: ("protection", 6),
          17: ("lighting", 3), 18: ("routing", 3),
          19: ("motors", 6), 20: ("reactive", 6), 21: ("panel_thermal", 6), 22: ("backup", 6), 23: ("lightning", 6), 24: ("hvac", 3), 25: ("phase_balance", 3), 26: ("raceway_sizing", 6), 27: ("coordination", 6), 28: ("special_locations", 6), 29: ("icc_decay", 6), 30: ("earthing", 6), 31: ("receptacles", 3)}   # 17 is not a slice of the 16-stage vocabulary: it is optional and `epc_calc_check` does not see it


def slice_spec(number):
    """The spec a slice object is built with (number and slug of the slice; the stage that groups it owns the table row)."""
    return _spec(number, SLICES[number][0], "", "", [], "implemented")

# The stages that run real work today (discipline functions, engine calls or manifests). Stage 4 runs only when the `transformer` inputs are given (MIG-39a; otherwise not_available;
# 12 needs a store). A test compares this tuple with the `wired` flag of every stage object.
WIRED_STAGES = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
