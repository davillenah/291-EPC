"""Shared pieces of the pipeline: the in-memory context, the stage result and the stage base class.

A stage prepares inputs and calls public functions; it never calculates or draws (PRD principle 3). A stage that
cannot run returns `not_available` with an explicit message and NO outputs, never a placeholder value.
"""
from dataclasses import asdict, dataclass, field

from disciplines.electrical_lv.rules.design_rules import check_preconditions

STATUSES = ("ok", "not_available", "blocked", "failed")
VERIFIER = "input-verifier"
PHASE1_MESSAGE = "not available in Phase 1"
WIRING_MESSAGE = "engine wiring: MIG-30c"


class StageInputError(ValueError):
    """The inputs of a stage are incomplete or wrong; the stage is `blocked`. `errors` lists every reason."""

    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = list(errors)


@dataclass
class PipelineContext:
    """Everything a run reads and fills, in memory. Without a `store` nothing is written; with one, only `pipeline.run()` records it."""

    pipeline_run_id: str = ""
    answers: dict = None
    inputs_dir: str = None
    load_list_path: str = None
    profile: dict = None
    inputs_manifest: dict = None
    loads: dict = None
    requirements: dict = None
    criteria: dict = None
    assumptions: list = None
    design_basis: dict = None
    engine_inputs: dict = None      # extra data for the calculation chain that the load list cannot carry (see stages/engine_calls.py)
    work_dir: str = None            # folder where the drawing stage may write; None = the stage is blocked (with a store: runs/<run id>/)
    mode: str = "production"        # `production` (strict, the default) or `edit` (norm records not verified do not stop the workflow; ADR-0035)
    revision: str = "R0"            # revision label of the deliverables issued by stage 12 (one transmittal `TR-NNN` per revision)
    store: object = None            # optional ProjectStore (store.py): when given, run() records the run in the project folder (MIG-31)
    results: dict = field(default_factory=dict)
    engine_cache: dict = field(default_factory=dict)   # raw engine results of this run (filled by the first stage that needs them)


@dataclass
class StageResult:
    """Outcome of one stage. A `not_available` result carries no outputs and no engine calls."""

    stage: int
    status: str
    outputs: dict = field(default_factory=dict)
    findings: list = field(default_factory=list)
    engine_calls: list = field(default_factory=list)
    message: str = ""
    reason: str = ""

    def __post_init__(self):
        if self.status not in STATUSES:
            raise ValueError(f"unknown stage status: {self.status!r}")
        if self.status == "not_available" and (self.outputs or self.engine_calls):
            raise ValueError("a not_available stage returns no outputs and calls no engine")

    def to_dict(self):
        return asdict(self)


def make_finding(n, run_id, document, field_name, value, expected, rule, action):
    """A finding-shaped dict (docs/harness/seeds/finding.schema.json); the rule id is carried in `clause`."""
    return {
        "id": f"F-{n:04d}", "run_id": run_id, "verifier": VERIFIER, "severity": "blocking",
        "document": document, "field": field_name, "value": value, "expected": expected,
        "clause": f"project criterion {rule}", "action": action,
        "evidence": [f"rule {rule}"], "status": "open",
    }


FLAG_ACTIONS = {
    "differential_ok": "The circuit needs a residual-current device: set `kind` to `rcbo` for it in `engine_inputs.circuits` (or give it a parent circuit of kind `rccb` or `rcbo`) and rerun; otherwise review it with the engineer of record.",
    "compliant": "The conductor does not meet the criteria of the calculation: check the load, the length and the installation method of the circuit (a bigger section or a shorter route may be needed), then rerun; or review it with the engineer of record.",
    "overload_ok": "The protection does not cover the conductor against overload: check the rating of the device against the current of the circuit and the capacity of the conductor, then rerun.",
    "coordination_ok": "The protection and the conductor are not coordinated: check the device rating and its tripping curve against the conductor, then rerun.",
    "protection_ok": "The protection does not meet the checks of the calculation: review the device rating, its breaking capacity and its curve for this circuit, then rerun.",
    "trip_ok": "The device may not trip on a short circuit at the end of the line: check the length of the circuit, the section and the curve of the device, then rerun.",
    "breaking_ok": "The breaking capacity of the device is below the short-circuit current at its point: choose a device with a higher breaking capacity, or review the short-circuit level given in the supply data.",
    "selectivity": "The devices upstream and downstream are not selective: review the ratings and curves of both, or the manufacturer's selectivity table, then rerun.",
    "panel_thermal_incomplete": "A device above the table of the engine has no dissipation: give the manufacturer's dissipation of each device in `engine_inputs.panel_thermal` and rerun.",
    "ra_complies": "The earth electrode resistance is above what the earthing system allows: review the electrode (more or longer rods, or a different arrangement) with the engineer of record, then rerun.",
    "phase_unbalance_complies": "The load is unbalanced between phases beyond the limit: redistribute the single-phase circuits among the phases, then rerun.",
    "fits_largest_size": "The conductors do not fit the largest raceway of the table: split the circuits among more raceways or choose another installation method, then rerun.",
    "special_location_complies": "The room is a special location and its circuits do not meet its requirements: review them with the engineer of record, then rerun.",
    "start_voltage_drop_complies": "The voltage drop while the motor starts is above the limit: review the section, the length or the starting method of the motor, then rerun.",
    "panel_thermal_complies": "The heat the devices dissipate is above what the enclosure admits: review the enclosure or its ventilation, or the devices, then rerun.",
}


def engine_finding(n, run_id, document, circuit, flag, value, expected):
    """A finding for a verdict the ENGINE returned (a boolean flag it computed); the stage only reports it."""
    return {
        "id": f"F-{n:04d}", "run_id": run_id, "verifier": "calc-check", "severity": "major",
        "document": document, "field": f"{circuit}/{flag}", "value": value, "expected": expected,
        "clause": f"engine result {flag}", "action": FLAG_ACTIONS.get(flag, "Review the engine result with the engineer of record."),
        "evidence": [f"engine flag {flag} of {circuit}"], "status": "open",
    }


class Stage:
    """One entry of the PRD section 12 table. Subclasses override `execute` (or declare why they cannot run)."""

    wired = False          # True once run() does real work (discipline function or engine call)
    wiring_task = None     # the migration task that will make the stage run; None = no engine in Phase 1

    def __init__(self, spec):
        self.spec = spec

    @property
    def number(self):
        return self.spec.number

    def unavailable_message(self):
        """Why the stage cannot run, or None when it can."""
        if self.wired:
            return None
        if self.spec.phase1_status == "planned":
            return PHASE1_MESSAGE + (f" ({self.wiring_task})" if self.wiring_task else "")
        if self.wiring_task == "MIG-30c":
            return WIRING_MESSAGE
        return f"not available yet: {self.wiring_task}"

    def reason_code(self):
        if self.spec.phase1_status == "planned":
            return "phase1_planned"
        return "wiring_pending" if self.wiring_task == "MIG-30c" else "pending_task"

    def result(self, status, **kwargs):
        return StageResult(self.number, status, **kwargs)

    def execute(self, context):  # pragma: no cover - overridden by every wired stage
        raise NotImplementedError

    def _blocked(self, context, errors, rule):
        run_id = context.pipeline_run_id
        findings = [make_finding(n, run_id, "pipeline", f"stage {self.number}", None, e, rule, "Provide the missing input.")
                    for n, e in enumerate(errors, start=1)]
        return self.result("blocked", findings=findings, message="; ".join(errors), reason="input")

    def run(self, context):
        message = self.unavailable_message()
        if message:
            return self.result("not_available", message=message, reason=self.reason_code())
        pre = check_preconditions(self.number, context, context.pipeline_run_id)
        if pre:
            return self.result("blocked", findings=pre, message=f"preconditions of stage {self.number} not met", reason="precondition")
        return self._guarded(context)

    def _guarded(self, context):
        try:
            return self.execute(context)
        except StageInputError as exc:
            return self._blocked(context, exc.errors, "ST-01")
        except Exception as exc:  # a stage must report, not crash the run
            return self.result("failed", message=f"{type(exc).__name__}: {exc}", reason="exception")
