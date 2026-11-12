# Approvals

One engineer of record per discipline (decision D20). Formal approval happens at four milestones, each recorded with date and the hash of what was signed:

1. **Design freeze**: inputs, criteria and assumptions are fixed before the draft.
2. **Acceptance of assumptions**: every assumed item with its reason.
3. **Review of unreviewed norm values**, per package: each register id used, its review state and hash. This records the state; it does not lift the IFC block.
4. **IFC block**: IFC needs points 1 to 3 current, no open blocking finding, and no unreviewed norm value used by the package (decision D21).

Only a person approves norm values or signs. The harness never invents the engineer's name, registration or date. Details: `docs/harness/SPEC.md` section 14.1.
