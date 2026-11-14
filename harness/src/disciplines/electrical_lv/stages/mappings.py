"""Mapping tables of the engine wiring (MIG-30c): data only, no calculation.

They say how a load of the load list becomes a circuit row of the board form that `epc_drawing.board_design` reads, and which
names the engines use. Nothing here is a norm value.
"""

# The engine tells the type of a circuit from the prefix of its tag (`L-` is lighting); the tag sent to the engine is
# `<prefix><load id>` unless the load id already starts with the prefix.
KIND_TAG_PREFIX = {"lighting": "L-", "receptacles": "T-", "motor": "M-", "special": "E-"}

# Topology (starter) of the circuit by load kind. A motor has none here on purpose: the starter is a design decision
# the engineer gives (`engine_inputs["circuits"][<load id>]["topology"]`); without it the stage is blocked.
KIND_TOPOLOGY = {"lighting": "single", "receptacles": "single", "special": "single"}

# Load type the demand-factor table of the engine is keyed by (`aea_demand.factor_demanda_sistema`); "" = the engine's "otros".
KIND_SYSTEM = {"lighting": "lighting", "receptacles": "receptacles", "motor": "power", "special": ""}

PHASE_CODE = {1: "1F", 3: "3F"}

# Units of the load list that the engine reads as they are.
POWER_UNITS_WITH_FP = ("W", "kW")

# Keys of a per-load override (`engine_inputs["circuits"][<load id>]`): the circuit keys of the board form.
OVERRIDE_KEYS = ("parent_tag", "topology", "phase_assigned", "fp", "efficiency", "kind", "notes", "cable_type", "method",
                 "insulation", "material", "grouped", "d2_column", "spacing", "route", "moments", "symbols", "length_m", "destination")

# Documents of PRD stage 11 whose engine does not exist yet: reported by name, never with a value.
PENDING_DOCUMENTS = ("specification", "cable list", "BOQ", "datasheets", "RFQ", "descriptive report")

# What the stages report as pending because no engine function produces it.
PENDING_ITEMS = {
    4: [{"item": "phase balance", "reason": "no engine function assigns circuits to phases (the parked backend does it in its own module)"}],
    5: [{"item": "demand total of the board", "reason": "no engine function applies the demand factors to the board load"}],
    11: [{"item": "thermal withstand k2S2", "reason": "the engine check needs the let-through energy of the breaker (manufacturer data), which the intake does not collect"}],
    12: [{"item": "earth electrode and soil study", "reason": "needs soil data that the intake does not collect yet"}],
}

ENGINE_CHAIN = "calculation/aea90364"
