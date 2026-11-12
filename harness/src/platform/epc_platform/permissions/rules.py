"""The RACI of PRD 5 and the hard rules of PRD 14.4 as data.

Evaluation order (see `core.check`): the DENY rules first, in order (the first one that matches decides and names its id), then the ALLOW
rules, then the default: deny (`D-99`). Nothing here runs code; edit the tables to change the policy and the tests to match.

The pipeline itself is not a role: it writes `ssot/`, `runs/`, `deliverables/` through its token (store.py). No role writes those folders.
"""
ENGINEER = "engineer_of_record"
REVIEWER = "reviewing_engineer"
ORCHESTRATOR = "orchestrator"
ELECTRICAL_LV = "electrical_lv"
CALC_CHECK = "calc_check"
DOCUMENTATION = "documentation"
PROCUREMENT = "procurement"

PEOPLE = (ENGINEER, REVIEWER)
AGENTS = (ORCHESTRATOR, ELECTRICAL_LV, CALC_CHECK, DOCUMENTATION, PROCUREMENT)
PRODUCERS = (ELECTRICAL_LV, DOCUMENTATION, PROCUREMENT)
ROLES = PEOPLE + AGENTS

INPUTS, SSOT, RUNS, DELIVERABLES, REVIEWS, TRANSMITTALS, AUDIT = (
    "inputs", "ssot", "runs", "deliverables", "reviews", "transmittals", "audit")
CONFIG_NORMATIVE, SCHEMAS, HARNESS_CODE = "config_normative", "schemas", "harness_code"
PROJECT_CLASSES = (INPUTS, SSOT, RUNS, DELIVERABLES, REVIEWS, TRANSMITTALS, AUDIT)
PATH_CLASSES = PROJECT_CLASSES + (CONFIG_NORMATIVE, SCHEMAS, HARNESS_CODE)

READ, WRITE, CREATE, DELETE, SIGN, APPROVE_NORM_VALUES, ISSUE = "read", "write", "create", "delete", "sign", "approve_norm_values", "issue"
ACTIONS = (READ, WRITE, CREATE, DELETE, SIGN, APPROVE_NORM_VALUES, ISSUE)
WRITES = (WRITE, CREATE)

# (rule id, reason, roles, actions, path classes, only when the inputs are frozen)
DENY = (
    ("D-01", "nobody deletes anything (PRD 17: the audit trail and the project history stay)", ROLES, (DELETE,), PATH_CLASSES, False),
    ("D-02", "only the engineer of record signs", tuple(r for r in ROLES if r != ENGINEER), (SIGN,), PATH_CLASSES, False),
    ("D-03", "only the engineer of record approves norm values", tuple(r for r in ROLES if r != ENGINEER), (APPROVE_NORM_VALUES,), PATH_CLASSES, False),
    ("D-04", "inputs are immutable once frozen", ROLES, WRITES, (INPUTS,), True),
    ("D-05", "segregation of duties: calc_check never writes what the producers produce", (CALC_CHECK,), WRITES, (SSOT, RUNS, DELIVERABLES, TRANSMITTALS), False),
    ("D-06", "segregation of duties: a producer never writes verification findings", PRODUCERS, WRITES, (REVIEWS,), False),
    ("D-07", "agents cannot write ssot, deliverables or config/normative directly (PRD 14.4; inputs: D-04 once frozen)", AGENTS, WRITES,
     (SSOT, DELIVERABLES, CONFIG_NORMATIVE), False),
    ("D-08", "ssot, runs and deliverables are written by the pipeline only", ROLES, WRITES, (SSOT, RUNS, DELIVERABLES), False),
    ("D-09", "the audit folder is appended by the platform event log only", ROLES, WRITES, (AUDIT,), False),
    ("D-10", "schemas and harness code change through code review (CODEOWNERS), not through a role", ROLES, WRITES, (SCHEMAS, HARNESS_CODE), False),
)

# (rule id, why, roles, actions, path classes)
ALLOW = (
    ("A-01", "everyone reads everything", ROLES, (READ,), PATH_CLASSES),
    ("A-02", "the engineer of record signs deliverables (RACI: approval and signature R/A)", (ENGINEER,), (SIGN,), (DELIVERABLES,)),
    ("A-03", "the engineer of record approves norm values (RACI: norm values review R/A)", (ENGINEER,), (APPROVE_NORM_VALUES,), (CONFIG_NORMATIVE,)),
    ("A-04", "issue: orchestrator responsible, engineer accountable (RACI: issue and transmittal)", (ENGINEER, ORCHESTRATOR), (ISSUE,),
     (DELIVERABLES, TRANSMITTALS)),
    ("A-05", "intake: the orchestrator and the engineer add inputs before the freeze (RACI: profile and inputs)", (ENGINEER, ORCHESTRATOR), WRITES, (INPUTS,)),
    ("A-06", "review: the people and calc_check record findings and corrections", (ENGINEER, REVIEWER, CALC_CHECK), WRITES, (REVIEWS,)),
    ("A-07", "the orchestrator and the engineer prepare transmittals", (ENGINEER, ORCHESTRATOR), (CREATE,), (TRANSMITTALS,)),
    ("A-08", "a person (the engineer of record) edits norm data; agents cannot", (ENGINEER,), WRITES, (CONFIG_NORMATIVE,)),
)
DEFAULT_RULE = ("D-99", "not allowed by any rule (default deny)")

# Who may trigger each workflow transition (RACI rows), see epc_platform.workflow.
TRIGGERS = {
    "complete_intake": (ENGINEER, ORCHESTRATOR),
    "start_run": (ORCHESTRATOR,),
    "finish_run": (ORCHESTRATOR,),
    "submit_for_review": (ENGINEER, ORCHESTRATOR),
    "record_corrections": (ENGINEER, REVIEWER),
    "rerun": (ENGINEER, ORCHESTRATOR),
    "approve": (ENGINEER,),
    "issue": (ENGINEER, ORCHESTRATOR),
}
