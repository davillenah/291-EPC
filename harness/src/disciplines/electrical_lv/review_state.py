"""The review state of a transmittal follows the workflow (SIM-06): `submit`, `approve` and `issue` write it in the manifest, the signer of `approve` included, and rewrite the cover of the transmittal.

The manifest of a run is `draft` and unsigned. After that it is only these fields that change, through `ProjectStore.record_review`:
  submit_for_review -> `for_review`
  approve           -> `approved_for_construction` in production (the D21 guard has checked the norm records), `approved` in edit mode (the package says it is not for production); `signed` = the actor and the date
  issue             -> `issued` (the signature stays)
The cover PDF (`TR-NNN_transmittal.pdf`) is rendered again with that state, the signer and the open `major` findings; it is not one of the files of the manifest, so its hash is in none.
A new run of a signed revision is still refused (the revision is closed): a correction is a new revision.
"""
import copy
import tempfile
from pathlib import Path

REVIEW_STATUS = {"submit_for_review": "for_review", "approve": "approved", "issue": "issued"}


def status_after(transition, manifest):
    """The `review_status` a manifest takes after a transition; None when the transition does not touch it."""
    if transition == "approve" and manifest.get("mode") != "edit":
        return "approved_for_construction"
    return REVIEW_STATUS.get(transition)


def reviewed(manifest, transition, signer, date):
    """The manifest after `transition`: its `review_status` and, for `approve`, `signed`. None when nothing changes."""
    status = status_after(transition, manifest)
    if status is None:
        return None
    out = copy.deepcopy(manifest)
    out["review_status"] = status
    if transition == "approve":
        out["signed"] = {"signer": signer, "date": date}
    return out


def _cover(store, token, manifest):
    """Render the cover of the transmittal again with the state of `manifest` (only when the run wrote one)."""
    rel = f"deliverables/{manifest['transmittal']}/{manifest['transmittal']}_transmittal.pdf"
    if not store.resolve(rel).is_file():
        return
    from disciplines.electrical_lv.stages import rendering
    project = manifest["title"].split()[0]
    data = rendering.transmittal_data(manifest["transmittal"], project, manifest["revision"], manifest["pipeline_run_id"], manifest["files"], manifest["normative_profile"]["norm_records"],
                                      manifest.get("mode", "production"), manifest["review_status"], manifest["signed"], manifest["findings"])
    with tempfile.TemporaryDirectory() as tmp:
        source, _call = rendering.render_transmittal(data, tmp, manifest["transmittal"])
        store.copy_deliverable(token, Path(tmp) / source, rel)


def reflect(store, token, transition, signer, date):
    """Apply `transition` to every manifest in force (not superseded): the manifest first, then its cover. Returns the transmittals changed."""
    changed = []
    for _rel, manifest in store.read_manifests():
        if manifest.get("superseded_by") is not None:
            continue
        new = reviewed(manifest, transition, signer, date)
        if new is None:
            continue
        store.record_review(token, new)
        _cover(store, token, new)
        changed.append(new["transmittal"])
    return changed
