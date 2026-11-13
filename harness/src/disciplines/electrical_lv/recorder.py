"""What `pipeline.run()` records in the project folder while it runs, when the context has a `ProjectStore`.

For every stage: one line in `epc-progress.txt`, one file `ssot/stage_<NN>_<slug>.json` (the full StageResult) and an update of
`master_project_state.json`. Stage 1 also writes `project_profile.json` and freezes `inputs/`; from stage 2 on, a changed,
added or removed input blocks the stage with a finding (rule IM-01). Everything goes through the store with the run's token. After stage 16 the manifests it built are written under `deliverables/<revision>/`.

Progress line format (`epc-progress.txt`, plain text, one line per stage, appended):

    <ISO timestamp> | run <pipeline_run_id> | stage <n> <slug> | <status> | <message>

The timestamp is the injected clock at the end of the stage (`-` when no clock was given); the message is the stage message on
one line (`-` when empty).

No timestamp is created here: the clock is the one given to `pipeline.run()`.
"""
import copy

from disciplines.electrical_lv.stages.base import make_finding

SCHEMA_VERSION = "0.1"
INTAKE = 1
PACKAGE = 16


def progress_line(timestamp, run_id, stage, res):
    message = " ".join((res.message or "").replace("|", "/").split()) or "-"
    return f"{timestamp or '-'} | run {run_id} | stage {stage.number} {stage.spec.slug} | {res.status} | {message}"


def renumbered(res, offset):
    """Copy of the result whose findings are numbered F-<offset+1>, F-<offset+2>, ... (same rule as the run summary)."""
    res = copy.deepcopy(res)
    for i, finding in enumerate(res.findings, start=offset + 1):
        finding["id"] = f"F-{i:04d}"
    return res


class RunRecorder:
    def __init__(self, store, token, run_id, clock=None):
        self.store, self.token, self.run_id, self.clock = store, token, run_id, clock
        self.entries, self.findings = [], []
        prior = store.read_state()
        self.revisions = copy.deepcopy(prior.get("revisions", []))
        self.signatures = copy.deepcopy(prior.get("signatures", []))

    def now(self):
        return self.clock() if self.clock else None

    def open(self, context):
        """The store owns `inputs/`; the drawing stage writes under `runs/<id>/` unless the caller chose a work_dir."""
        context.inputs_dir = str(self.store.inputs_dir)
        if context.work_dir is None:
            context.work_dir = self.store.make_run_dir(self.token, self.run_id)
        self._save("running")

    def adopt(self, reused, stages):
        """Count the stages reused from an earlier run as part of this one: their entries, findings and one progress line each ("reused")."""
        prior = {e["number"]: e for e in self.store.read_state().get("stages", [])}
        for res, stage in zip(reused, stages):
            self.findings += copy.deepcopy(res.findings)
            self.entries.append(prior.get(stage.number) or {"number": stage.number, "slug": stage.spec.slug, "status": res.status, "started": None,
                                                               "finished": None, "finding_count": len(res.findings)})
            line = progress_line(self.now(), self.run_id, stage, res).replace(f"| {res.status} |", "| reused |", 1)
            self.store.append_progress(self.token, line)
        self._save("running")

    def check_inputs(self, stage):
        """A blocked result for stages 2+ when the inputs differ from the frozen manifest (or were never frozen), else None."""
        if stage.number <= INTAKE:
            return None
        findings = self._input_findings()
        if not findings:
            return None
        return stage.result("blocked", findings=findings, reason="inputs_changed",
                            message=f"{len(findings)} input file(s) changed since intake")

    def _input_findings(self):
        if self.store.is_frozen():
            return self.store.verify_inputs_unchanged(self.run_id)
        return [make_finding(1, self.run_id, "pipeline", "inputs", "not frozen", "frozen at intake", "IM-01", "Run stage 1 (intake) first.")]

    def record(self, context, stage, res, started):
        """Persist one finished stage; returns the copy of the result with run-wide finding ids."""
        res = renumbered(res, len(self.findings))
        finished = self.now()
        self.store.write_ssot(self.token, f"stage_{stage.number:02d}_{stage.spec.slug}.json", res.to_dict())
        if stage.number == INTAKE and res.status == "ok":
            self._intake(context)
        if stage.number == PACKAGE and res.status == "ok":
            self._publish(res)
        self.findings += res.findings
        self.entries.append({"number": stage.number, "slug": stage.spec.slug, "status": res.status, "started": started,
                             "finished": finished, "finding_count": len(res.findings)})
        self.store.append_progress(self.token, progress_line(finished, self.run_id, stage, res))
        self._save("running")
        return res

    def _intake(self, context):
        self.store.write_profile(self.token, context.profile)
        if not self.store.is_frozen():
            self.store.freeze_inputs(self.token)

    def _publish(self, res):
        """Stage 16: write the deliverable manifests it built, then mark the superseded ones (all through the store, with this run's token)."""
        for item in res.outputs["manifests"]:
            self.store.write_manifest(self.token, item["manifest"])
        for item in res.outputs["superseded"]:
            self.store.update_manifest(self.token, item["manifest"])

    def finish(self, last_stage_number):
        statuses = [e["status"] for e in self.entries]
        if "failed" in statuses:
            status = "failed"
        elif "blocked" in statuses:
            status = "blocked"
        else:
            status = "completed" if self.entries and self.entries[-1]["number"] == last_stage_number else "paused"
        self._save(status)

    def _save(self, status):
        state = {"schema_version": SCHEMA_VERSION, "status": status, "pipeline_run_id": self.run_id, "stages": copy.deepcopy(self.entries),
                 "revisions": copy.deepcopy(self.revisions),
                 "open_findings": [copy.deepcopy(f) for f in self.findings if f.get("status", "open") == "open"],
                 "signatures": copy.deepcopy(self.signatures)}
        self.store.write_state(self.token, state)
