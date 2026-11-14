"""The studies of the project made from the results of the run: short circuit, selectivity, load schedule and the memo of runs (raceways).

Ported from the studies of the old web backend (`sld/studies.py`, `sld/loadschedule.py`, `layout/raceways.py`): the discipline calculates nothing, it puts together what the engine chain
(`board_memo`) and the plan engine already calculated, in the structured form of the other documents of stage 11 (sections of paragraphs, lists, tables and gaps; see `doc_blocks.py`).
Every figure is read from the memo of the board, the load schedule of stage 3 or the routing of stage 3; a figure the memo does not carry is `None`, never an estimate.
"""
import copy

from disciplines.electrical_lv.stages.doc_blocks import items, paragraph, section, table

STATUS = "draft"
STUDY_PENDING = "norm factors are typical values still to be verified against the standard: the study is not approved for construction"


def _doc(name, title, sections):
    return {"document": name, "title": title, "status": STATUS, "sections": sections}


def _failing(circuits):
    """(circuit, protection) of the circuits whose protection fails in breaking capacity or in magnetic trip."""
    return [(c, c["proteccion"]) for c in circuits if not c["proteccion"]["icu_ok"] or c["proteccion"]["disparo_ok"] is False]


def _why(p):
    out = []
    if not p["icu_ok"]:
        out.append(f"breaking capacity {p['icu_ka']} kA below the Icc {p['icc_a'] / 1000} kA")
    if p["disparo_ok"] is False:
        out.append(f"minimum Icc {p['icc_min_a']} A below {p['k_max']} x In = {p['k_max'] * p['In']} A")
    return "; ".join(out)


def short_circuit_study(memo):
    """The short-circuit study of the board: what each protection withstands (breaking capacity against the Icc of the bars, magnetic trip with the minimum Icc)."""
    board, circuits = memo["board"], memo["circuits"]
    bad = _failing(circuits)
    rows = [(c["tag"], p["disp"], p["curva"], p["In"], p["icu_ka"], p["icu_ok"], p["icc_min_a"], p["k_max"], p["disparo_ok"]) for c in circuits for p in [c["proteccion"]]]
    summary = section(1, "Summary", table(["board", "system", "Icc bars (kA)", "circuits", "failing"], [(board["name"], board["system"], board["icc_ka"], len(circuits), len(bad))]),
                      paragraph("Every protection has a breaking capacity not below the Icc of its bars and trips with the minimum Icc.") if not bad else items(f"{c['tag']}: {_why(p)}" for c, p in bad))
    detail = section(2, "Detail", table(["tag", "device", "curve", "In (A)", "Icu (kA)", "breaking capacity ok", "Icc min (A)", "k max", "trip ok"], rows))
    return _doc("short_circuit_study", "Short-circuit study", [summary, detail, section(3, "Assumptions", paragraph(STUDY_PENDING))])


def selectivity_study(memo):
    """The selectivity study: each protection against the one upstream (the pairs of the memo) and the count of total, partial and to review."""
    pairs, counts = memo["selectividad"], memo["resumen"]["selectividad"]
    rows = [(p["aguas_arriba"], p["aguas_abajo"], p["resultado"]) for p in pairs]
    return _doc("selectivity_study", "Protection selectivity study",
                [section(1, "Summary", table(["total", "partial", "to review"], [(counts["total"], counts["parcial"], counts["revisar"])])),
                 section(2, "Pairs", table(["upstream", "downstream", "result"], rows)), section(3, "Assumptions", paragraph(STUDY_PENDING))])


def load_schedule(schedule):
    """The load schedule of the board: one row per circuit with its current and power, from the load schedule of stage 3."""
    rows = [(c["circuit"], c["load_id"], c["phases"], c["fp"], c["p_kw"], c["ib_a"], c["parent"]) for c in schedule["circuits"]]
    total = sum(c["p_kw"] for c in schedule["circuits"] if not c["parent"])
    return _doc("load_schedule", "Load schedule",
                [section(1, "Circuits", table(["circuit", "load", "phases", "power factor", "P (kW)", "Ib (A)", "fed from"], rows)),
                 section(2, "Total", paragraph(f"Sum of the circuits that hang from the board: {round(total, 3)} kW (the demand factors are applied by the engine in the memo, not here)."))])


def raceway_memo(routing):
    """The memo of runs: for each floor the circuits that were routed and the trays and conduits with the cables they hold (the schedule of the plan engine)."""
    sections = []
    for n, (floor, data) in enumerate(sorted(((routing or {}).get("floors") or {}).items()), start=1):
        held = [(k["tag"], k["kind"], k["cables"], ", ".join(k["circuits"])) for k in data["schedule"]["containers"]]
        routes = [(tag, r["found"], r.get("cable_length_m"), r.get("max_distance_m"), r.get("moment_length_m")) for tag, r in sorted(data["circuits"].items())]
        sections.append(section(n, f"Floor {floor}", paragraph("Routes of the circuits (metres)."), table(["circuit", "reached", "cable length", "farthest load", "moment length"], routes),
                                paragraph("Trays (BN) and conduits (CN) with the cables they hold."), table(["run", "kind", "cables", "circuits"], held)))
    return _doc("raceway_memo", "Memo of cables and raceways", sections or [section(1, "Floors", paragraph("No floor was routed."))])


def build(context, memo, routing):
    """{name: document} of the studies of the run; `routing` is the routing section of stage 3 (or None)."""
    stage3 = context.results.get(3)
    schedule = stage3.outputs.get("load_schedule") if stage3 is not None and stage3.status == "ok" else None
    docs = {"short_circuit_study": short_circuit_study(memo), "selectivity_study": selectivity_study(memo)}
    if schedule:
        docs["load_schedule"] = load_schedule(schedule)
    if routing:
        docs["raceway_memo"] = raceway_memo(routing)
    return copy.deepcopy(docs)
