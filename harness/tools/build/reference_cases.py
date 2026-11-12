"""Reference-case suite for the AEA 90364 calculation engine (REPORTS; it does not gate and it never changes the engine).

Each case (harness/src/engines/calculation/aea90364/reference_cases/cases/*.json) states an expected value that is
  (a) a closed-form result computed in the case from stated inputs and a stated formula, or
  (b) a value the repo's own data/rule files state (JSON pointer in `expected_source` / `repo_refs`), or
  (c) null with `needs_official_value` (only the official text, or an owner decision, can settle it).
This script calls the engine for each case (one small adapter per case family, below), compares and prints a table.

  python harness/tools/build/reference_cases.py              # table on stdout
  python harness/tools/build/reference_cases.py --report     # also writes harness/docs/REFERENCE_CASES.md (Spanish, for the owner)
  python harness/tools/build/reference_cases.py --only j_    # only the cases whose id contains the text
  python harness/tools/build/reference_cases.py --strict     # exit 1 if any case differs or could not run (default: always 0)

Statuses: pass | differ | needs_official_value (no expected value: the engine result is shown) | not_run (adapter could not call the engine).
Test discovery of the gate does not see these files (no tests/ folder, no test_*.py).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import epc_paths as EP  # noqa: E402

ROOT = EP.REPO
CASES_DIR = EP.engine_dir("aea90364") / "reference_cases" / "cases"
REPORT = EP.DOCS / "REFERENCE_CASES.md"
for _p in ("aea90364", "receptacles", "lighting"):
    sys.path.insert(0, str(EP.engine_src(_p)))


class NotRun(Exception):
    """The adapter cannot call the engine for this case."""


# ------------------------------------------------------------------ helpers
def _pget(rel_file: str, pointer: str):
    cur = json.loads((ROOT / EP.current_location(rel_file)).read_text(encoding="utf-8"))   # frozen cases still name the pre-MIG-37a places
    for tok in [t.replace("~1", "/").replace("~0", "~") for t in pointer.strip("/").split("/")]:
        cur = cur[int(tok)] if isinstance(cur, list) else cur[tok]
    return cur


def _num(v, n=6) -> str:
    if isinstance(v, bool) or v is None:
        return str(v)
    if isinstance(v, (int, float)):
        return f"{v:.{n}g}"
    return str(v)


def _par(inp: dict, extra: dict | None = None) -> dict:
    from epc_aea90364 import aea_ampacity as AMP
    c = {"AISLACION": inp.get("aislacion", "PVC"), "MATERIAL": inp.get("material", "Cu"), "METODO": inp.get("metodo", "B1"),
         "AGRUP_CIRCUITOS": inp.get("agrupamiento", inp.get("circuitos", 1)), "TEMP_AMBIENTE_C": inp.get("temp_C", 40)}
    c.update(extra or {})
    return AMP.parametros(c)


def _run_pipeline(rows: list, criterios=None):
    from epc_aea90364 import aea_pipeline as P
    det: dict = {}
    datos, avisos = P.calculate({"TENSION_V": 380, "ICC_KA": 10, "FP_DEFAULT": 0.85}, rows, criterios=criterios, detalle=det)
    return datos, det, avisos


def _row(tag, amps, length=10.0, desc="carga"):
    return {"TAG": tag, "DESCRIPCION": desc, "CARGA": amps, "UNIDAD_CARGA": "A", "FASE": "3F", "LONGITUD_m": length, "TOPOLOGY": "single"}


# ------------------------------------------------------------------ adapters: each returns {"value": ..., "info": "..."}
def vd_three_phase(c):
    from epc_aea90364 import voltage_drop as VD
    i = c["inputs"]
    r = VD.caida_tension(3, i["I_A"], i["L_m"], i["R_ohm_km"], i["X_ohm_km"], i["cos_phi"], i["Un_V"])
    return {"value": r["delta_u_v"], "info": f"dU% = {r['delta_u_pct']:.4f} % de {i['Un_V']} V"}


def vd_table_unit(c):
    from epc_aea90364 import aea_voltage_drop as VD
    s = c["inputs"]["S_mm2"]
    return {"value": VD.drop_unit_table(s if s != int(s) else int(s)), "info": "valor de la tabla 771.19.IV copiada en el motor (el pipeline NO la usa: usa la fórmula con R a 70 C)"}


def sc_basic(c):
    from epc_aea90364 import short_circuit as SC
    i = c["inputs"]
    red = {"sk_va": i["Sk_MVA"] * 1e6, "x_r": i["X_R_red"]} if "Sk_MVA" in i else None
    r = SC.calcular_ik(i["Un_V"], SC.factor_c(6), red=red, trafo={"sn_va": i["Sn_kVA"] * 1e3, "uk_pct": i["uk_pct"]})
    return {"value": r["ik_a"], "info": f"|Z| = {r['z_ohm'] * 1000:.4f} mohm, c = {r['c']}; R = {r['r_ohm']:.3e}, X = {r['x_ohm']:.5f} ohm"}


def sc_kappa(c):
    from epc_aea90364 import short_circuit as SC
    i = c["inputs"]
    return {"value": SC.factor_kappa(i["R_ohm"], i["X_ohm"]), "info": ""}


def sc_peak(c):
    from epc_aea90364 import short_circuit as SC
    i = c["inputs"]
    r = SC.calcular_ik(400.0, SC.factor_c(6), trafo={"sn_va": 1e6, "uk_pct": 6})
    return {"value": SC.corriente_pico(r["ik_a"], r["r_ohm"], r["x_ohm"]), "info": f"Ik'' = {r['ik_a']:.2f} A; kappa = {SC.factor_kappa(r['r_ohm'], r['x_ohm']):.4f}"}


def ct_smin(c):
    from epc_aea90364 import cable_thermal as CT, aea_conductors as CO
    i = c["inputs"]
    import re
    m = re.match(r"\s*([<>]?)\s*([\d.]+)", str(i.get("seccion_cable", "")))
    section = None if not m else float(m.group(2)) + (1.0 if m.group(1) == ">" else 0.0)   # "> 300 mm2" -> a section just above 300
    k_eng = CT.k_material(i.get("material", "Cu"), i.get("aislacion", "PVC"), section)
    return {"value": CT.seccion_minima_mm2(i["I_A"], i["t_s"], k_eng),
            "info": f"cable_thermal usa k = {k_eng} (sección {section}); aea_conductors.k_adiabatico_771('pvc_sobre_300','cu') = {CO.k_adiabatico_771('pvc_sobre_300', 'cu')} y ('pvc_hasta_300','cu') = {CO.k_adiabatico_771('pvc_hasta_300', 'cu')}"}


def amp_iz(c):
    from epc_aea90364 import aea_ampacity as AMP
    i = c["inputs"]
    par = _par(i)
    v = AMP.iz(par, i["S_mm2"], 3)
    f = AMP.factores(par, True)
    return {"value": v, "info": f"factores del motor: {f}; Iz base = {AMP.iz_base(par, i['S_mm2'], 3)} A"}


def amp_grouping(c):
    from epc_aea90364 import aea_ampacity as AMP, aea_tables as T
    i = c["inputs"]
    par = _par(i)
    f = AMP.factores(par, True)["f_agrup"]
    info = f"f_agrup del motor = {f:.5f}"
    n = i["circuitos"]
    if i["metodo"] == "B1":
        row = [r for r in T.cargar()["factores_correccion"]["771.16.IV"]["filas"] if r["item"] == "1"][0]
        ns, fs = row["numero_de_circuitos"], row["factores"]
        sup = [x for x in ns if x >= n]
        inf = [x for x in ns if x <= n]
        info += f"; conteos vecinos tabulados: {inf[-1] if inf else None} -> {fs[ns.index(inf[-1])] if inf else None}, {sup[0] if sup else None} -> {fs[ns.index(sup[0])] if sup else None}"
    else:
        info += "; la tabla D2 llega a 6 circuitos (en contacto 0,5): el motor usa min(n, 6) sin aviso"
    try:
        iz7 = AMP.iz(_par(i, {"AISLACION": "pvc"}), 25, 3)
        info += f"; Iz Cu 25 mm2 3 cargados con este agrupamiento = {iz7:.2f} A"
    except ValueError as e:
        info += f"; (Iz 25 mm2: {e})"
    return {"value": f, "info": info}


def tt_ra_earthing(c):
    from epc_aea90364 import aea_earthing as E
    r = E.ra_maxima(c["inputs"]["I_dn_A"])
    return {"value": r["adoptada"], "info": f"col1 (50 V) = {r['col1_50v']:.1f}, col2 (24 V) = {r['col2_24v']:.1f}, adoptada = {r['adoptada']:.1f} ohm"}


def tt_ra_protection(c):
    from epc_aea90364 import aea_protection as PR
    i = c["inputs"]["I_dn_A"]
    return {"value": PR.ra_maxima_tt(i), "info": "ra_maxima_tt(ia_a): la Ra adoptada de aea_earthing.ra_maxima (D11)"}


def tt_ra_memo(c):
    from epc_aea90364 import board_memo as BM
    idn_ma = c["inputs"]["I_dn_A"] * 1000.0
    tag = "T1"
    circ = {tag: {"description": "tomas", "parent_tag": ""}}
    dat = {"In": 16, "Ib": 10.0, "S": 2.5, "icu": 10, "disp": "MCB"}
    det = {tag: {"tipo": "tomacorrientes", "kind": "rcbo", "topologia": "single", "cumple": True, "iz_a": 24.0, "icc_min_a": 500.0,
                 "s_termica_mm2": 2.5, "largo_m": 10.0, "ruta": [], "padre": ""}}
    try:
        res = BM._circuit(tag, circ, dat, det, {}, idn_ma, "TT", 6000.0)
    except Exception as e:  # the memo internals may need more fields
        raise NotRun(f"board_memo._circuit no se pudo llamar con un circuito sintético: {type(e).__name__}: {e}")
    d = res["diferencial"]
    return {"value": d["ra_max_tt_ohm"], "info": f"diferencial del memo = {d}; el memo usa aea_earthing.ra_maxima (D11)"}


def earth_times(c):
    from epc_aea90364 import aea_earthing as E
    d = _pget(f"{EP.NORM_DATA_REL['aea90364']}/aea_tables.json", "/constantes/771.18.III_tiempos_desconexion_s")
    diffs, total = [], 0
    for esq in ("TN", "TT"):
        eng, rep = E.TIEMPOS_DESCONEXION_S[esq], d[esq]
        for a, b in zip(eng, rep):
            for x, y in zip(a, b):
                total += 1
                if x != y:
                    diffs.append(f"{esq} {a[0]}: motor {a} vs datos {b}")
        if len(eng) != len(rep):
            diffs.append(f"{esq}: distinta cantidad de rangos")
    return {"value": len(diffs), "info": f"{total} valores comparados, {len(diffs)} distintos" + ("" if not diffs else ": " + "; ".join(diffs))
            + "; el motor rotula la tabla como 771.18.I y los datos como 771.18.III"}


def tn_zs(c):
    from epc_aea90364 import aea_earthing as E
    i = c["inputs"]
    r = E.zs_lazo(i["U0_V"], i["Icc_barras_kA"], i["S_fase_mm2"], i["S_PE_mm2"], i["L_m"])
    return {"value": r["zs_ohm"], "info": f"Z fuente = {r['zfuente_ohm']:.5f}, R lazo = {r['r_ohm']:.4f}, X lazo = {r['x_ohm']:.4f} ohm"}


def tn_zsmax(c):
    from epc_aea90364 import aea_earthing as E
    return {"value": E.zs_maxima(c["inputs"]["U0_V"], c["inputs"]["Ia_A"]), "info": ""}


def tn_verify(c):
    from epc_aea90364 import aea_earthing as E, aea_protection as PR
    i = c["inputs"]
    zs = E.zs_lazo(i["U0_V"], i["Icc_barras_kA"], i["S_fase_mm2"], i["S_PE_mm2"], i["L_m"])["zs_ohm"]
    r = PR.verifica_tn(zs, i["Ia_A"], i["U0_V"])
    return {"value": r["zs_ia_v"], "info": f"verifica_tn: cumple = {r['cumple']} (límite {r['limite_v']} V); se espera cumple = False"}


def tn_limits(c):
    from epc_aea90364 import aea_earthing as E, aea_protection as PR
    i = c["inputs"]
    r = PR.verifica_tn(1.0, i["Ia_A"], i["U0_V"])
    zmax = E.zs_maxima(i["U0_V"], i["Ia_A"])
    lim = r["limite_v"] / i["Ia_A"]
    return {"value": lim, "info": f"verifica_tn: Zs <= {lim:.5f} ohm; zs_maxima: {zmax:.5f} ohm; diferencia {(lim / zmax - 1) * 100:.2f} %"}


def rod(c):
    from epc_aea90364 import aea_earthing as E
    i = c["inputs"]
    simp = i.get("modo") == "simplificada"
    return {"value": E.resistance_rod(i["rho_ohm_m"], i["L_m"], i["d_m"], simp), "info": f"L/d = {i['L_m'] / i['d_m']:g}" + (" (modo simplificado)" if simp else "")}


def rod_jump(c):
    from epc_aea90364 import aea_earthing as E
    i = c["inputs"]
    a = E.resistance_rod(i["rho_ohm_m"], i["L_m"], i["d_antes_m"], True)
    b = E.resistance_rod(i["rho_ohm_m"], i["L_m"], i["d_despues_m"], True)
    return {"value": (b / a - 1) * 100, "info": f"simplificada: R({i['L_d_antes']:g}) = {a:.4f} ohm, R({i['L_d_despues']:.2f}) = {b:.4f} ohm"}


def react_qc(c):
    from epc_aea90364 import aea_reactive as R
    i = c["inputs"]
    return {"value": R.reactiva_a_compensar(i["P_kW"], i["cos_phi_1"], i["cos_phi_2"]), "info": ""}


def react_bank(c):
    from epc_aea90364 import aea_reactive as R
    i = c["inputs"]
    b = R.banco(i["Qc_kvar"], i["U_V"])
    return {"value": b["instalado_kvar"], "info": f"banco = {b}"}


def light_ad(c):
    from epc_aea90364 import aea_lightning as LG
    i = c["inputs"]
    return {"value": LG.superficie_captacion_m2(i["L_m"], i["W_m"], i["H_m"]), "info": ""}


def light_nd(c):
    from epc_aea90364 import aea_lightning as LG
    i = c["inputs"]
    return {"value": LG.impactos_directos_anuales(i["Ng_km2_anio"], i["Ad_m2"], "aislada"), "info": ""}


def overload(c):
    from epc_aea90364 import aea_conductors as CO, aea_protection as PR, policy
    i = c["inputs"]
    i2 = PR.i2_convencional(i["In_A"], i["tipo"])
    r = CO.verify_overload(i["Ib_A"], i["In_A"], i["Iz_A"], i2)
    return {"value": i2 / (policy.k_max_i2_iz() * i["Iz_A"]), "info": f"I2 = {i2:.2f} A; verify_overload = {r}"}


def pipeline_i2(c):
    datos, det, avisos = _run_pipeline([_row("C1", 14.0)])
    d = det["C1"]
    has = [k for k in d if "i2" in k.lower() or "coord" in k.lower()]
    return {"value": bool(has), "info": f"claves del detalle del pipeline: {sorted(d)}; claves con I2/coordinación: {has or 'ninguna'}; In = {d['in_a']} A, Iz = {d['iz_a']} A, S = {datos['C1']['S']} mm2"}


def board_head(c):
    from epc_aea90364 import board_feeders as BF, aea_demand as DM
    rows = [_row("C1", 10.0), _row("C2", 20.0), _row("C3", 30.0)]
    datos, det, _ = _run_pipeline(rows)
    head = BF.head_current(datos, det)
    coef = DM.coef_simultaneity_770(3)
    return {"value": head, "info": f"head_current (suma aritmética) = {head} A; ponderada con coef 770 de 3 circuitos ({coef}) = {coef * head:.2f} A; el cable de acometida se dimensiona con la suma"}


def recept(c):
    import epc_receptacles
    i = c["inputs"]
    doc = {"schema_version": "1.0", "receptacles": [{"id": "tug", "name": "Socket outlet", "kind": "general", "poles": 2, "rated_a": 10, "power_va": 100, "height_m": 0.3, "ip": "IP20"}],
           "rooms": [{"id": "R1", "name": "Room", "use": i["uso"], "length_m": i["largo_m"], "width_m": i["ancho_m"], "receptacle": "tug"}]}
    r = epc_receptacles.run(doc).as_dict()["rooms"][0]
    return {"value": r["required"], "info": f"motor: {r['estimate']['reason']} (confianza {r['estimate']['confidence']})"}


def pe(c):
    from epc_aea90364 import aea_conductors as CO, aea_earthing as E
    s = c["inputs"]["S_fase_mm2"]
    mod = c["engine_call"]["module"]
    v = CO.pe_section(s) if mod == "aea_conductors" else E.seccion_pe_mm2(s)
    return {"value": v, "info": f"aea_conductors.pe_section = {CO.pe_section(s)}; aea_earthing.seccion_pe_mm2 = {E.seccion_pe_mm2(s)}"}


def default_ins(c):
    from epc_aea90364 import aea_pipeline as P
    r = P.resolver_criterios(None)
    return {"value": r[3], "info": f"resolver_criterios(None) -> aislación '{r[3]}', material '{r[2]}'; resolver_criterios({{}}) -> '{P.resolver_criterios({})[3]}'"}


def ins_effect(c):
    out = []
    for crit in (None, {"insulation": "XLPE"}):
        datos, det, _ = _run_pipeline([_row("C1", 30.0, 40.0)], crit)
        d = det["C1"]
        out.append(f"criterios={crit}: S = {datos['C1']['S']} mm2, Iz = {d['iz_a']} A, aislación {d['aislacion']}, método {d['metodo']}, dU = {d['du_acum_pct']} %")
    return {"value": None, "info": " | ".join(out)}


def c_min(c):
    from epc_aea90364 import short_circuit as SC, aea_pipeline as P
    return {"value": SC.C_MIN_BT, "info": f"aea_pipeline.C_MIN_BT = {P.C_MIN_BT}"}


def c_max(c):
    from epc_aea90364 import short_circuit as SC, aea_pipeline as P
    return {"value": SC.C_MAX_BT_TOL_6, "info": f"aea_pipeline.C_MAX_BT = {P.C_MAX_BT}"}


ADAPTERS = {f.__name__: f for f in (vd_three_phase, vd_table_unit, sc_basic, sc_kappa, sc_peak, ct_smin, amp_iz, amp_grouping, tt_ra_earthing, tt_ra_protection,
                                    tt_ra_memo, earth_times, tn_zs, tn_zsmax, tn_verify, tn_limits, rod, rod_jump, react_qc, react_bank, light_ad, light_nd,
                                    overload, pipeline_i2, board_head, recept, pe, default_ins, ins_effect, c_min, c_max)}
ADAPTERS["tt_ra_memo"] = tt_ra_memo
ADAPTERS["pe"] = pe
ADAPTERS["recept"] = recept


# ------------------------------------------------------------------ run and compare
def run_case(c: dict) -> dict:
    res = {"id": c["id"], "title": c["title_es"], "severity": c["severity_if_fails"], "status": "not_run", "engine": None, "info": "", "diff": None, "reason": ""}
    exp = c.get("expected")
    stale = []
    for r in c.get("repo_refs", []):
        try:
            now = _pget(r["file"], r["pointer"])
            if now != r["value"]:
                stale.append(f"{r['pointer']}: caso {r['value']!r}, repo hoy {now!r}")
        except Exception as e:
            stale.append(f"{r['pointer']}: no se pudo leer ({type(e).__name__})")
    res["stale"] = stale
    try:
        fn = ADAPTERS.get(c["engine_call"]["adapter"])
        if fn is None:
            raise NotRun(f"no hay adaptador '{c['engine_call']['adapter']}'")
        out = fn(c)
    except NotRun as e:
        res["reason"] = str(e)
        return res
    except Exception as e:
        res["reason"] = f"el motor falló: {type(e).__name__}: {e}"
        return res
    v = out["value"]
    res["engine"], res["info"] = v, out.get("info", "")
    if exp is None:
        res["status"] = "needs_official_value"
        return res
    ev, tol = exp["value"], exp.get("tolerance_pct", 0.0)
    if isinstance(ev, str) or isinstance(v, str) or isinstance(v, bool):
        res["status"] = "pass" if v == ev else "differ"
        return res
    if "puntos" in exp.get("unit", ""):
        diff = v - ev
        res["diff"] = ("pp", diff)
        res["status"] = "pass" if abs(diff) <= tol else "differ"
    else:
        diff = (v - ev) / abs(ev) * 100.0 if ev else (0.0 if v == ev else math.inf)
        res["diff"] = ("%", diff)
        res["status"] = "pass" if abs(diff) <= tol else "differ"
    return res


def load_cases(only: str | None = None) -> list:
    cases = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CASES_DIR.glob("*.json"))]
    return [c for c in cases if not only or only in c["id"]]


def _diff_txt(r) -> str:
    if r["diff"] is None:
        return "-"
    unit, d = r["diff"]
    return f"{d:+.3f} {'%' if unit == '%' else 'pp'}"


LABEL = {"pass": "COINCIDE", "differ": "DIFIERE", "needs_official_value": "SIN VALOR OFICIAL", "not_run": "NO CORRIÓ"}


def print_table(results: list, cases: dict) -> None:
    w = max(len(r["id"]) for r in results)
    print(f"{'caso':<{w}}  {'estado':<18} {'esperado':>14} {'motor':>14} {'dif':>12}  gravedad")
    for r in results:
        e = cases[r["id"]].get("expected")
        print(f"{r['id']:<{w}}  {LABEL[r['status']]:<18} {_num(e['value']) if e else 'null':>14} {_num(r['engine']):>14} {_diff_txt(r):>12}  {r['severity']}")
    n = {s: sum(1 for r in results if r["status"] == s) for s in LABEL}
    print(f"\nTotal {len(results)}: coinciden {n['pass']}, difieren {n['differ']}, sin valor oficial {n['needs_official_value']}, no corrieron {n['not_run']}")
    for r in results:
        if r["stale"]:
            print(f"AVISO {r['id']}: el dato del repo cambió desde que se escribió el caso: {r['stale']}")


MEANING = {
    "pass": "El motor coincide con el valor de referencia dentro de la tolerancia.",
    "differ": "El motor se aparta del valor de referencia más que la tolerancia. Hay que decidir si el defecto está en el motor o en el criterio del caso.",
    "needs_official_value": "No hay valor esperado: solo el texto oficial o una decisión del dueño lo fija. Se muestra qué hace hoy el motor.",
    "not_run": "El adaptador no pudo llamar al motor; no hay comparación.",
}
SEV = {"safety": "seguridad", "major": "importante", "minor": "menor"}


def write_report(results: list, cases: dict) -> None:
    n = {s: [r for r in results if r["status"] == s] for s in LABEL}
    L = ["# Casos de referencia independientes del motor de cálculo (AEA 90364)", "",
         "Generado por `python harness/tools/build/reference_cases.py --report`. Este documento **informa**; no es una compuerta y no cambia el motor.", "",
         "Cada caso recalcula el valor esperado de forma independiente: (a) fórmula cerrada con entradas declaradas, (b) un valor que los propios datos del repo declaran (se cita el puntero JSON) o (c) sin valor esperado cuando solo el texto oficial, o una decisión del dueño, puede resolverlo. No se cita ninguna norma de memoria.", "",
         "## Resumen", "", "| Estado | Casos |", "|---|---|"]
    for s in LABEL:
        L.append(f"| {LABEL[s]} | {len(n[s])} |")
    L += [f"| **Total** | **{len(results)}** |", ""]
    if n["differ"]:
        L += ["### Casos que difieren", "", "| Caso | Gravedad si falla | Esperado | Motor | Diferencia |", "|---|---|---|---|---|"]
        for r in n["differ"]:
            e = cases[r["id"]]["expected"]
            L.append(f"| `{r['id']}` | {SEV[r['severity']]} | {_num(e['value'])} {e['unit']} | {_num(r['engine'])} | {_diff_txt(r)} |")
        L.append("")
    if n["needs_official_value"]:
        L += ["### Casos sin valor oficial (decisión del dueño o texto de la norma)", "", "| Caso | Gravedad | Motor hoy |", "|---|---|---|"]
        for r in n["needs_official_value"]:
            L.append(f"| `{r['id']}` | {SEV[r['severity']]} | {_num(r['engine'])} |")
        L.append("")
    if n["not_run"]:
        L += ["### Casos que no corrieron", ""] + [f"- `{r['id']}`: {r['reason']}" for r in n["not_run"]] + [""]
    L += ["## Detalle por caso", ""]
    for r in results:
        c = cases[r["id"]]
        e = c.get("expected")
        L += [f"### {c['id']} — {c['title_es']}", "", f"- **Estado:** {LABEL[r['status']]}   |   **Gravedad si falla:** {SEV[r['severity']]}   |   **Magnitud:** `{c['quantity']}`",
              "- **Entradas:** " + ", ".join(f"{k} = {json.dumps(v, ensure_ascii=False)}" for k, v in c["inputs"].items()),
              f"- **Fórmula y cuenta:** {c['formula']}",
              ("- **Valor esperado:** " + f"{_num(e['value'])} {e['unit']} (tolerancia {e['tolerance_pct']} {'pp' if 'puntos' in e['unit'] else '%'}); fuente: `{c['expected_source']}`") if e
              else f"- **Valor esperado:** ninguno ({'decisión del dueño' if c.get('null_kind') == 'owner_decision' else 'valor oficial pendiente'})",
              f"- **Llamada al motor:** `{c['engine_call']['module']}.{c['engine_call']['function']}` — {c['engine_call']['mapping']}",
              f"- **Resultado del motor:** {_num(r['engine']) if r['status'] != 'not_run' else 'no corrió: ' + r['reason']}",
              f"- **Diferencia:** {_diff_txt(r)}"]
        if r["info"]:
            L.append(f"- **Detalle del motor:** {r['info']}")
        if r["stale"]:
            L.append(f"- **AVISO, dato del repo cambió:** {r['stale']}")
        L += [f"- **Qué significa:** {MEANING[r['status']]} {c['note_es']}", ""]
    REPORT.write_text("\n".join(L), encoding="utf-8")
    print(f"Informe escrito en {REPORT.relative_to(ROOT)}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--report", action="store_true", help="write harness/docs/REFERENCE_CASES.md")
    ap.add_argument("--only", help="run only the cases whose id contains this text")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any case differs or does not run")
    a = ap.parse_args(argv)
    cases = load_cases(a.only)
    if not cases:
        print("no hay casos")
        return 1 if a.strict else 0
    results = [run_case(c) for c in cases]
    by_id = {c["id"]: c for c in cases}
    print_table(results, by_id)
    if a.report:
        write_report(results, by_id)
    bad = any(r["status"] in ("differ", "not_run") for r in results)
    return 1 if (a.strict and bad) else 0


if __name__ == "__main__":
    sys.exit(main())
