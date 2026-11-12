"""The PRD section 12 table (16 stages) as a fixed ordered tuple. Titles, engines and status words are copied from the PRD.

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
    _spec(2, "requirements", "Requirements and design basis (criteria, profile, assumptions)", "quality (design basis)",
          [("quality", "design_basis")], "planned"),
    _spec(3, "input_verification", "Input verification (plans vs loads vs requirements)", "cad/plan, validation",
          [("cad", "plan"), ("validation", None)], "in development"),
    _spec(4, "load_schedule", "Load schedule and phase balance", "calculation/load_balance",
          [("calculation", "load_balance")], "implemented (inside aea90364)"),
    _spec(5, "demand", "Demand and simultaneity (771.9)", "calculation/load_balance",
          [("calculation", "load_balance")], "implemented"),
    _spec(6, "supply_transformer", "Supply and transformer sizing", "calculation/transformer_sizing",
          [("calculation", "transformer_sizing")], "planned"),
    _spec(7, "board_structure", "Board structure and circuit assignment", "calculation, validation",
          [("calculation", None), ("validation", None)], "implemented"),
    _spec(8, "feeder_sizing", "Feeder and circuit sizing (Ib ≤ In ≤ Iz, I2 ≤ 1.45 Iz, installation method)",
          "calculation/feeder_sizing", [("calculation", "feeder_sizing")], "implemented"),
    _spec(9, "voltage_drop", "Voltage drop, accumulated (D17)", "calculation/voltage_drop",
          [("calculation", "voltage_drop")], "implemented"),
    _spec(10, "short_circuit", "Short-circuit currents (max/min)", "calculation/short_circuit",
          [("calculation", "short_circuit")], "implemented"),
    _spec(11, "protection_selectivity", "Protection and selectivity; thermal withstand k²S²", "calculation/selectivity",
          [("calculation", "selectivity")], "implemented"),
    _spec(12, "earthing", "Earthing and fault protection (TT: Ra; TN: Zs = c_min·U0/Ia; disconnection times)",
          "calculation/grounding", [("calculation", "grounding")], "implemented"),
    _spec(13, "calc_check", "Deterministic verification (calc_check): recalculation, format, cross-document consistency",
          "validation", [("validation", None)], "in development"),
    _spec(14, "drawings", "Drawings: SLD, board layouts", "cad", [("cad", None)], "implemented (SLD)"),
    _spec(15, "documents", "Documents and lists: calculation report, specification, cable list, terminal-block list, BOQ, datasheets, RFQ, descriptive report",
          "quality, procurement", [("quality", None), ("procurement", None)], "in part"),
    _spec(16, "package_issue", "Package issue: manifests, review status, transmittal", "platform", [("platform", None)], "planned"),
)

# The stages that run real work today (discipline functions, engine calls or manifests). Stage 6 runs only when the `transformer` inputs are given (MIG-39a; otherwise not_available;
# 16 needs a store). A test compares this tuple with the `wired` flag of every stage object.
WIRED_STAGES = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16)
