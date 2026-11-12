"""The rule table: every rule id, who raises it, its severity and the engine function whose docstring carries the clause (if the rule comes from a norm).

Severity by meaning: `blocking` = a number is not a number, or an issued file differs from what was recorded; `major` = a value or verdict does not agree with
the engine or with another document; `minor` = a value that cannot be built or read as stated; `note` = something that could not be checked.
"""
from epc_calc_check.findings import Rule

CC, FC, DC = "calc-check", "format-check", "document-check"
AEA = "epc_aea90364."

RULES = {r.id: r for r in (
    # A. recalculation: the engine's own functions on the inputs the engine had; any difference means a stage or a mapping altered a number
    Rule("CC-R00", CC, "note", "A quantity cannot be recomputed from what the run carries (no input is guessed)", None),
    Rule("CC-R01", CC, "major", "Iz equals the engine ampacity function on the same inputs", None),
    Rule("CC-R02", CC, "major", "Own voltage drop equals the engine voltage-drop function on the same inputs", None),
    Rule("CC-R03", CC, "major", "PE and neutral sections equal the engine rule functions", AEA + "aea_conductors.pe_section"),
    Rule("CC-R04", CC, "major", "Conventional operating current I2 equals k2 x In of the engine", AEA + "aea_protection.i2_convencional"),
    Rule("CC-R05", CC, "major", "Icu is the first standard value of the engine series not below the busbar Icc", None),
    # B. invariants: comparisons between the numbers the engine reported, no new number
    Rule("CC-B01", CC, "major", "Ib <= In <= Iz", AEA + "aea_protection.in_max_por_iz"),
    Rule("CC-B02", CC, "major", "I2 <= k_max x Iz (k_max from the engine policy)", AEA + "policy.k_max_i2_iz"),
    Rule("CC-B03", CC, "major", "The voltage-drop verdict agrees with the drops, the limit and Iz", AEA + "aea_voltage_drop.limite_caida_pct"),
    Rule("CC-B04", CC, "major", "The drop limit applied is one of the limits the engine reports", None),
    Rule("CC-B05", CC, "major", "Icu >= Icc and the breaking-capacity flag agrees", None),
    Rule("CC-B06", CC, "major", "Icc of the circuits equals the busbar Icc and is not below Icc min", None),
    Rule("CC-B07", CC, "major", "Icc min against the magnetic trip limit and the trip flag agree", None),
    Rule("CC-B08", CC, "major", "The overload and coordination flags agree with the numbers", AEA + "aea_protection.in_max_por_iz"),
    Rule("CC-B09", CC, "major", "The section is not below the minimum section nor below the internal section", AEA + "aea_conductors.section_min_circuit"),
    Rule("CC-B10", CC, "major", "The accumulated drop is the parent's accumulated drop plus the own drop", None),
    Rule("CC-B11", CC, "major", "A differential is present where the engine requires one and its flag agrees", None),
    Rule("CC-B12", CC, "major", "In, Icu and the section belong to the standard series of the engine", None),
    # C. format
    Rule("CC-F01", FC, "major", "The run has the shape of a pipeline result (stage numbers, statuses, names)", None),
    Rule("CC-F02", FC, "major", "A key the stage must return is missing", None),
    Rule("CC-F03", FC, "blocking", "A number is NaN or infinite", None),
    Rule("CC-F04", FC, "major", "A numeric field is not a number or a flag is not a boolean", None),
    Rule("CC-F05", FC, "major", "A circuit tag or an id is duplicated", None),
    Rule("CC-F06", FC, "major", "A hash is not 64 lowercase hexadecimal characters", None),
    Rule("CC-F07", FC, "minor", "A quantity has no unit or a value without a number", None),
    Rule("CC-F08", FC, "major", "A finding does not follow the finding schema or its id repeats (inside a stage; across the run once renumbered)", None),
    Rule("CC-F09", FC, "major", "The circuit stages do not list the same circuits", None),
    Rule("CC-F10", FC, "major", "A manifest does not validate against the deliverable manifest schema", None),
    Rule("CC-F11", FC, "major", "A revision label or run id is not valid or the manifests disagree on it", None),
    Rule("CC-F12", FC, "major", "A check could not run on the data (the data does not have the expected shape)", None),
    # D. cross-document consistency
    Rule("CC-D01", DC, "major", "The same quantity differs between two stages", None),
    Rule("CC-D02", DC, "major", "A value of the calculation memo differs from the stages", None),
    Rule("CC-D03", DC, "major", "The hash recorded for a document does not match its content", None),
    Rule("CC-D04", DC, "major", "The memo summary differs from the stages", None),
    Rule("CC-D05", DC, "major", "The drawing summary differs from the stages", None),
    Rule("CC-D06", DC, "blocking", "A manifest or recorded hash differs from the hash of the file", None),
    Rule("CC-D07", DC, "note", "A field exists in one place only, so it cannot be compared", None),
)}
