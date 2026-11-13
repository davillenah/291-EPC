# `integration`

Status: **in development**

Integration tests of the pipeline over the engines, run through the real `epc` CLI in process (temp projects root, injected clock). Helpers: `synthetic_lv.py`.

| Test | What it proves |
| --- | --- |
| `test_synthetic_lv_small.py` | The synthetic project (`../golden_projects/synthetic_lv_small/`) runs 12 stages to `deliverables/R0/` with one valid, complete, hash-consistent draft manifest per deliverable. |
| `test_reproducibility.py` | Two runs with the same run id and clock are byte-identical except the DXF files (the DXF writer stamps time and GUIDs) and the hashes that embed them. |
| `test_synthetic_permissions.py` | Agent roles are denied on protected classes (and logged), the guard hook blocks writes into real project files, approval needs the engineer and D21, tampering is detected (IM-01, CC-D06). |

Needs the engine packages on `PYTHONPATH` (the gate's `harness-tests` environment sets it).
