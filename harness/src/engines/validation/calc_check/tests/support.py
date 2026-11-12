"""Test support: a clean pipeline result in its JSON form, built from the engines directly (no discipline), so each test can seed one error.

The row shapes copy the stage outputs of `disciplines/electrical_lv/stages/calc_stages.py` (field name -> engine source); the seeded-error suite in
`harness/tests/unit/test_calc_check_seeded.py` does the same against the real pipeline.
"""
import copy
import hashlib
import json

from epc_aea90364 import board_memo
from epc_drawing import board_design

FORM = {
    "board": {"name": "T1", "voltage_v": 380, "system": "TN", "icc_ka": 25, "fp_default": 0.85, "project": "T1"},
    "circuits": [
        {"tag": "L-01", "description": "LIGHTING", "load": 1.5, "unit": "kW", "phase": "1F", "topology": "single", "kind": "mcb", "fp": 0.9, "length_m": 30},
        {"tag": "T-01", "description": "SOCKETS", "load": 2.2, "unit": "kW", "phase": "1F", "topology": "single", "kind": "mcb", "fp": 0.9, "length_m": 20},
        {"tag": "M-01", "description": "PUMP", "load": 5.5, "unit": "kW", "phase": "3F", "topology": "dol", "kind": "mccb", "fp": 0.85, "efficiency": 0.9, "length_m": 25},
        {"tag": "SUB", "description": "FEEDER", "load": 80, "unit": "A", "phase": "3F", "topology": "single", "kind": "mccb", "length_m": 40},
    ]}
TAGS = ("L-01", "T-01", "M-01", "SUB")
SOURCES = {"datos": 0, "detalle": 1, "memo": 2}
FIELDS = {
    4: {"ib_a": ("detalle", ("ib_a",)), "p_kw": ("detalle", ("p_kw",)), "phases": ("detalle", ("fases",)), "fp": ("detalle", ("fp",)), "parent": ("detalle", ("padre",))},
    7: {"type": ("detalle", ("tipo",)), "parent": ("detalle", ("padre",)), "device_kind": ("detalle", ("kind",)), "topology": ("detalle", ("topologia",)),
        "device": ("datos", ("disp",)), "chain": ("detalle", ("cadena",)), "solution": ("detalle", ("solucion",))},
    8: {"in_a": ("datos", ("In",)), "ib_a": ("datos", ("Ib",)), "s_mm2": ("datos", ("S",)), "s_internal_mm2": ("detalle", ("s_termica_mm2",)), "iz_a": ("detalle", ("iz_a",)),
        "min_section_mm2": ("detalle", ("seccion_min_mm2",)), "material": ("detalle", ("material",)), "insulation": ("detalle", ("aislacion",)),
        "method": ("detalle", ("metodo",)), "route": ("detalle", ("ruta",)), "route_limiting": ("detalle", ("ruta_limitante",)), "pe_mm2": ("detalle", ("pe_mm2",)),
        "neutral_mm2": ("detalle", ("neutro_mm2",)), "transition": ("memo", ("transicion",)), "i2_a": ("memo", ("proteccion", "i2_a")),
        "overload_ok": ("memo", ("proteccion", "sobrecarga_ok")), "coordination_ok": ("memo", ("proteccion", "coordinacion_ok")), "compliant": ("detalle", ("cumple",))},
    9: {"length_m": ("detalle", ("largo_m",)), "limit_pct": ("detalle", ("limite_pct",)), "own_pct": ("detalle", ("du_propia_pct",)),
        "accumulated_pct": ("detalle", ("du_acum_pct",)), "du_pct": ("datos", ("dU",)), "compliant": ("detalle", ("cumple",))},
    10: {"icu_ka": ("datos", ("icu",)), "icc_a": ("memo", ("proteccion", "icc_a")), "icc_min_a": ("detalle", ("icc_min_a",)), "breaking_ok": ("memo", ("proteccion", "icu_ok")),
         "trip_ok": ("memo", ("proteccion", "disparo_ok")), "k_min": ("memo", ("proteccion", "k_min")), "k_max": ("memo", ("proteccion", "k_max"))},
    11: {"device": ("datos", ("disp",)), "device_kind": ("memo", ("proteccion", "kind")), "curve": ("memo", ("proteccion", "curva")), "in_a": ("memo", ("proteccion", "In")),
         "overload_ok": ("memo", ("proteccion", "sobrecarga_ok")), "coordination_ok": ("memo", ("proteccion", "coordinacion_ok")),
         "protection_ok": ("memo", ("proteccion", "cumple"))},
    12: {"differential": ("memo", ("diferencial",)), "differential_ok": ("memo", ("diferencial", "cumple"))},
}


def _pick(source, path):
    for key in path:
        source = source.get(key) if isinstance(source, dict) else None
    return copy.deepcopy(source)


def engine_chain():
    data = board_design.groups_in(copy.deepcopy(FORM), None)
    res = board_design.calculate(data, None)
    memo = board_memo.build(data["board"], data["circuits"], res["datos"], res["detalle"], res["limites"], res["conductor"], res["rcd_ma"], upstream=None, validated=False,
                            feeders=res["acometidas"])
    return data, res, memo


def rows(number, res, memo):
    by_tag = {c["tag"]: c for c in memo["circuits"]}
    out = []
    for tag in res["datos"]:
        src = {"datos": res["datos"][tag], "detalle": res["detalle"][tag], "memo": by_tag[tag]}
        row = {"circuit": tag, "load_id": tag}
        row.update({name: _pick(src[kind], path) for name, (kind, path) in FIELDS[number].items()})
        out.append(row)
    return out


def sha(data):
    return hashlib.sha256(data).hexdigest()


def doc_hash(doc):
    return sha(json.dumps(doc, sort_keys=True, ensure_ascii=False).encode("utf-8"))


def stage(number, outputs=None, status="ok", findings=None):
    return {"stage": number, "status": status, "outputs": outputs or {}, "findings": findings or [], "engine_calls": [], "message": "", "reason": ""}


def manifest(deliverable_id, output_sha, run_id="run1", revision="R0"):
    return {"deliverable_id": deliverable_id, "title": "Title", "revision": revision, "pipeline_run_id": run_id, "inputs": [{"path": "inputs/a.csv", "sha256": "a" * 64}],
            "engines": [{"name": "calculation/aea90364", "version": "1.6.0"}],
            "normative_profile": {"revisions": {}, "norm_records": [{"id": "x", "review_status": "pending review"}]},
            "output_sha256": output_sha, "findings": [], "review_status": "draft", "signed": None, "superseded_signature": None, "supersedes": None, "superseded_by": None}


def clean_run():
    """(run_result, project, files): a run with stages 1-5 and 7-12 from the engine, 14 and 15 (documents from the engine), 16 (two manifests)."""
    data, res, memo = engine_chain()
    dxf = b"0\nSECTION\n0\nEOF\n"
    docs = {"calculation_memo": board_memo.memoria_doc(memo), "project_summary": board_memo.sintesis_doc(memo)}
    documents = [{"name": n, "sha256": doc_hash(d), "document": d} for n, d in docs.items()]
    worst = max(v["dU"] for v in res["datos"].values())
    bad = [t for t, d in res["detalle"].items() if not d["cumple"]]
    summary = {"name": "T1", "ok": True, "circuits": len(res["datos"]), "groups": {}, "non_compliant": bad, "diagrams": ["sld"], "log": [f"OK SLD_T1 circuitos 4 dU max {round(worst, 2)}"]}
    results = [
        stage(1, {"profile": {}, "inputs_manifest": {"files": [{"path": "inputs/a.csv", "sha256": "a" * 64}], "manifest_sha256": "b" * 64},
                  "loads": {"loads": [{"id": "L-01", "power": {"value": 1.5, "unit": "kW"}}]}}),
        stage(2, {"design_basis": {}}), stage(3, {"verified": True, "manifest_sha256": "b" * 64}),
        stage(4, {"circuits": rows(4, res, memo), "pending": []}), stage(5, {"circuits": [], "pending": []}), stage(6, status="not_available"),
        stage(7, {"circuits": rows(7, res, memo), "board": copy.deepcopy(memo["board"]), "supply": {}, "differential_groups_added": {}, "contract_check": {"errores": []}}),
        stage(8, {"circuits": rows(8, res, memo), "engine_warnings": []}),
        stage(9, {"circuits": rows(9, res, memo), "limits_pct": copy.deepcopy(res["limites"])}),
        stage(10, {"circuits": rows(10, res, memo), "busbar_icc_ka": FORM["board"]["icc_ka"]}),
        stage(11, {"circuits": rows(11, res, memo), "selectivity": [], "selectivity_summary": {}, "pending": []}),
        stage(12, {"circuits": rows(12, res, memo), "earthing_system": "TN", "rcd_ma": res["rcd_ma"], "pending": []}),
        stage(13, status="not_available"),
        stage(14, {"directory": "drawings/T1/out", "files": [{"path": "SLD_T1.dxf", "bytes": len(dxf), "sha256": sha(dxf)}], "summary": summary}),
        stage(15, {"documents": documents, "memo_summary": copy.deepcopy(memo["resumen"]), "pending_documents": []}),
    ]
    mans = [manifest("T1-DRW-SLD_T1", sha(dxf)), manifest("T1-DOC-calculation_memo", documents[0]["sha256"])]
    rows16 = [{"deliverable_id": mans[0]["deliverable_id"], "source": "drawings/T1/out/SLD_T1.dxf", "manifest": "deliverables/R0/a.manifest.json"},
              {"deliverable_id": mans[1]["deliverable_id"], "source": None, "manifest": "deliverables/R0/b.manifest.json"}]
    results.append(stage(16, {"revision": "R0", "manifests": [{"path": rows16[0]["manifest"], "manifest": mans[0]}, {"path": rows16[1]["manifest"], "manifest": mans[1]}],
                              "transmittal": {"deliverables": rows16}}))
    run = {"pipeline_run_id": "run1", "results": results}
    project = {"circuits": {t: {"TEMP_AMBIENTE_C": res["detalle"][t]["instalacion"]["t_amb"], "TEMP_SUELO_C": res["detalle"][t]["instalacion"]["t_suelo"],
                                "RESIST_TERMICA_KMW": res["detalle"][t]["instalacion"]["rho"]} for t in res["datos"]}}
    return json.loads(json.dumps(run)), project, {"drawings/T1/out/SLD_T1.dxf": dxf}


def stage_of(run, number):
    return next(r for r in run["results"] if r["stage"] == number)


def row_of(run, number, tag):
    return next(r for r in stage_of(run, number)["outputs"]["circuits"] if r["circuit"] == tag)
