"""The project lifecycle: init -> intake_done -> running -> draft_ready -> in_review -> corrected -> (rerun) running ... -> approved -> issued.

TRANSITIONS: name -> (from state, to state). Who may trigger each one is in `permissions.rules.TRIGGERS` (RACI); `approve` also needs
the permission to `sign` deliverables and `issue` the permission to `issue` them (both checked with `permissions.enforce`).

Guards of `approve` and `issue` (D21): refused while any norm record listed by the latest manifests (those not superseded) is not
`verified`, and while the project has no manifest at all. A transition also writes its state in the manifests in force (`review_state.py`): `for_review`, `approved`/`approved_for_construction` with the signer and the date, `issued`.

A transition is applied only if every guard passes: it is then written to `reviews/workflow.json` through the project store (a
short write session of its own, `workflow-<n>`) and appended to the event log as `ok`. A refusal appends a `denied` event and raises.
"""
from disciplines.electrical_lv import review_state
from disciplines.electrical_lv.store import ProjectStore
from epc_platform.permissions import Decision, PermissionDenied, enforce, may_trigger
from epc_platform.permissions import rules as R

STATES = ("init", "intake_done", "running", "draft_ready", "in_review", "corrected", "approved", "issued")
TRANSITIONS = {
    "complete_intake": ("init", "intake_done"),
    "start_run": ("intake_done", "running"),
    "finish_run": ("running", "draft_ready"),
    "submit_for_review": ("draft_ready", "in_review"),
    "record_corrections": ("in_review", "corrected"),
    "rerun": ("corrected", "running"),
    "approve": ("in_review", "approved"),
    "issue": ("approved", "issued"),
}
GUARDED = ("approve", "issue")
NOT_A_TRIGGER = "W-01"
PERMISSION_OF = {"approve": (R.SIGN, R.DELIVERABLES), "issue": (R.ISSUE, R.DELIVERABLES)}


class WorkflowError(ValueError):
    """A transition that does not exist or does not start from the current state."""


class WorkflowBlocked(WorkflowError):
    """The D21 guard: an unreviewed norm record (or no manifest) blocks approval and issue."""


def unverified_records(store):
    """Ids of the norm records, listed by the latest manifests, that are not verified; ['<no manifest>'] when there is none."""
    latest = [m for _, m in store.read_manifests() if m.get("superseded_by") is None]
    if not latest:
        return ["<no manifest>"]
    return sorted({r["id"] for m in latest for r in m["normative_profile"]["norm_records"] if r["review_status"] != "verified"})


def open_findings(store, severity):
    """Findings of `severity` carried by the latest manifests (those not superseded)."""
    latest = [m for _, m in store.read_manifests() if m.get("superseded_by") is None]
    return [f.get("id") for m in latest for f in m.get("findings", []) if f.get("severity") == severity]


class Workflow:
    def __init__(self, project_dir, log, store=None):
        self.store = store or ProjectStore(project_dir)
        self.log = log

    @property
    def state(self):
        record = self.store.read_workflow()
        return record["state"] if record else "init"

    def history(self):
        record = self.store.read_workflow()
        return list(record["history"]) if record else []

    def allowed_transitions(self):
        """Names of the transitions that start from the current state."""
        return sorted(n for n, (src, _) in TRANSITIONS.items() if src == self.state)

    def transition(self, name, role, actor_id, run_id="workflow", review=None):
        """Apply a transition if it exists, starts from the current state, the role may trigger it and its guards pass. Returns the new state.

        `review` (optional, plain JSON) is stored as `reviews/<transition>-<n>.json` in the same write session (corrections, MIG-33b).
        """
        try:
            new_state = self._check(name, role, actor_id, run_id)
        except (WorkflowError, PermissionDenied) as exc:
            if not isinstance(exc, PermissionDenied) or exc.decision.rule_id == NOT_A_TRIGGER:  # enforce() already logged its own refusal
                self._log(name, role, actor_id, run_id, "denied", {"reason": str(exc)})
            raise
        old = self.state
        entry = {"from": old, "to": new_state, "transition": name, "role": role, "actor_id": actor_id, "pipeline_run_id": run_id}
        self._save(new_state, self.history() + [entry], run_id, review)
        self._log(name, role, actor_id, run_id, "ok", self._detail(old, new_state))
        return new_state

    # -- internals -----------------------------------------------------------------------------------------------------------
    def _check(self, name, role, actor_id, run_id):
        if name not in TRANSITIONS:
            raise WorkflowError(f"unknown transition {name!r}")
        src, dst = TRANSITIONS[name]
        if self.state != src:
            raise WorkflowError(f"{name} needs state {src}, the project is in {self.state}")
        if not may_trigger(role, name):
            raise PermissionDenied(f"{role} may not trigger {name}", Decision(False, "RACI: not a trigger of this transition", NOT_A_TRIGGER))
        if name in PERMISSION_OF:
            action, path_class = PERMISSION_OF[name]
            enforce(role, action, path_class, log=self.log, actor_id=actor_id, run_id=run_id, target=name)
        self.exempt = self._guard(name)
        return dst

    def _guard(self, name):
        """True when the D21 guard was not applied because of the edit mode, False when it passed or the transition has none; raises `WorkflowBlocked` when it blocks."""
        if name not in GUARDED:
            return False
        self._no_blocking()
        if self._edit_mode():
            return True
        self._d21()
        return False

    def _detail(self, old, new):
        """The detail of the `ok` event of a transition: from and to, and for an edit-mode step that the D21 guard was not applied."""
        return dict({"from": old, "to": new}, **({"mode": "edit", "d21": "not applied (edit mode)"} if getattr(self, "exempt", False) else {}))

    def _edit_mode(self):
        """True when the project is in edit mode and every manifest in force was made in edit mode (ADR-0035): the unverified norm records do not stop approve and issue. A project with no manifest, or with
        one made in production, keeps the D21 guard as it is."""
        if self.store.read_mode() != "edit":
            return False
        latest = [m for _, m in self.store.read_manifests() if m.get("superseded_by") is None]
        return bool(latest) and all(m.get("mode") == "edit" for m in latest)

    def _no_blocking(self):
        """A `blocking` finding open in the manifests in force stops approve and issue in every mode (SIM-07): it is fixed and the run repeated, or the engineer corrects it first."""
        bad = open_findings(self.store, "blocking")
        if bad:
            raise WorkflowBlocked(f"{len(bad)} blocking finding(s) still open ({', '.join(map(str, bad[:5]))}{' ...' if len(bad) > 5 else ''})")

    def _d21(self):
        bad = unverified_records(self.store)
        if bad:
            shown = ", ".join(bad[:5]) + (" ..." if len(bad) > 5 else "")
            raise WorkflowBlocked(f"D21: {len(bad)} norm record(s) not verified or no manifest ({shown})")

    def _save(self, state, history, run_id, review=None):
        with self.store.pipeline_session(f"workflow-{len(history)}") as token:
            if review is not None:
                self.store.write_review(token, f"{history[-1]['transition']}-{len(history)}.json", review)
            self.store.write_workflow(token, {"state": state, "history": history})
            review_state.reflect(self.store, token, history[-1]["transition"], history[-1]["actor_id"], str(self.log._clock()))

    def _log(self, name, role, actor_id, run_id, result, detail):
        self.log.append({"pipeline_run_id": run_id, "actor": {"role": role, "id": actor_id}, "action": f"transition:{name}",
                         "target": ".epc/reviews/workflow.json", "result": result, "detail": detail})
