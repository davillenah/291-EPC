"""The technical specification (pliego), draft, with a PROVISIONAL structure (PLG-01: the owner has not chosen the single structure yet; this one is a first proposal to be optimised).

The discipline writes no number and invents no norm value: every figure is read from the results of the run (the load list, the lighting and routing of stage 3, the voltage-drop limits of stage 6, the
cable list of stage 11) and every datum the project does not have is a `gap` block (`[DEFINIR]`, with who must give it). The structure follows the correspondence of PLG-01 between the nine chapters of the
old skill and the sections of the new agent: Objective, Scope, Descriptive memo, Normative framework, General conditions of execution, Technical requirements, Tests, Acceptance criteria, Technical
documentation, Responsibilities of the contractor, Provisional and final reception. It is built only when stage 3 routed the floors (without it the specification stays pending).

A document is {"document", "status", "structure", "sections": [{"id", "title", "blocks"}], "gaps"}; a block is a paragraph, a list, a table or a gap.
"""
import copy

from disciplines.electrical_lv.stages.doc_blocks import gap, items, paragraph, section, table

STRUCTURE = "provisional (PLG-01): a proposal to be optimised, not the owner's structure"
REFERENCE = "Makes and models are given as a reference or an approved equivalent, never as the only option."


def _site(context):
    profile = context.profile or {}
    return {"code": profile.get("project_code", ""), "client": (profile.get("client") or {}).get("name", ""), "type": (profile.get("site") or {}).get("installation_type", ""),
            "supply": profile.get("supply") or {}, "norms": (profile.get("normative_profile") or {})}


def _objective(site):
    return section(1, "Objective", paragraph(f"This specification sets the technical requirements for the low-voltage electrical installation of project {site['code']} ({site['type']}) for {site['client']}."),
                   paragraph("The values it quotes come from the calculation of the platform for this project; the contractor keeps the detail engineering and the final selection of equipment."))


def _scope(context, rows):
    areas = [(a["id"], a["name"]) for a in (context.loads or {}).get("areas", [])]
    kinds = {}
    for load in (context.loads or {}).get("loads", []):
        kinds[load["kind"]] = kinds.get(load["kind"], 0) + 1
    return section(2, "Scope", paragraph("The installation covers the areas and loads below."), table(["area", "name"], areas),
                   table(["kind of load", "circuits"], sorted(kinds.items())), paragraph(f"The cable list has {len(rows)} sized circuit(s)."))


def _memo(site, context):
    supply = site["supply"]
    sc = supply.get("short_circuit_level") or {}
    lines = [f"Earthing system: {supply.get('earthing_system', '')}.", f"Supply voltage: {(supply.get('voltage') or {}).get('value', '')} {(supply.get('voltage') or {}).get('unit', '')}.",
             f"Available short-circuit level: {sc.get('value', '')} {sc.get('unit', '')} ({sc.get('origin', '')})."]
    floors = ((context.results.get(3).outputs.get("routing") or {}).get("floors") or {}) if context.results.get(3) else {}
    lines += [f"Floor {f}: {len(d['proposed'])} branch circuit(s), {len(d['schedule']['containers'])} tray or conduit section(s)." for f, d in sorted(floors.items())]
    return section(3, "Descriptive memo", items(lines), gap("name and registration of the engineer of record", "engineer of record"))


def _norms(site):
    revisions = [(part, rev) for part, rev in sorted((site["norms"].get("revisions") or {}).items()) if rev]
    return section(4, "Normative framework", paragraph(f"Jurisdiction: {site['norms'].get('jurisdiction', '')}. The parts of AEA 90364 that apply, with the revision the project adopts:"),
                   table(["part", "revision"], revisions),
                   paragraph("Norm values that the platform has not had reviewed by a person are typical values to be verified; they are not approved for construction."))


def _conditions():
    return section(5, "General conditions of execution", items(["Work follows the issued drawings and the cable list; any change is submitted for approval before it is built.",
                                                                 "Materials are new, of the type and rating the calculation gives, and keep their identification until accepted.", REFERENCE]),
                   gap("work schedule, site access and coordination with other trades", "project manager"))


def _protections(rows):
    return table(["circuit", "from", "to", "In (A)", "Ib (A)"], [(r["circuit"], r["from"], r["to"], r["in_a"], r["ib_a"]) for r in rows])


def _conductors(rows):
    return table(["circuit", "material", "insulation", "section (mm2)", "method", "length (m)", "drop (%)"],
                 [(r["circuit"], r["material"], r["insulation"], r["s_mm2"], r["method"], r["length_m"], r["du_pct"]) for r in rows])


def _raceways(context):
    floors = ((context.results.get(3).outputs.get("routing") or {}).get("floors") or {}) if context.results.get(3) else {}
    by_kind = {}
    for data in floors.values():
        for c in data["schedule"]["containers"]:
            by_kind[c["kind"]] = by_kind.get(c["kind"], 0) + 1
    return table(["kind of run (BN tray, CN conduit)", "sections"], sorted(by_kind.items()))


def _lighting(context):
    study = (context.results.get(3).outputs.get("lighting") or {}) if context.results.get(3) else {}
    counts = study.get("counts") or {}
    return paragraph(f"Lighting: {counts.get('luminaires', 0)} luminaire(s) in {counts.get('rooms', 0)} room(s), placed by the lighting calculation (draft).")


def _technical(context, rows):
    return section(6, "Technical requirements", paragraph("Boards and protective devices, as calculated:"), _protections(rows), paragraph("Conductors, as sized by the voltage drop by electrical moments:"),
                   _conductors(rows), paragraph("Trays and conduits, as laid out for the project:"), _raceways(context), _lighting(context),
                   gap("lighting fittings and receptacle models, and the makes accepted as reference", "client or project engineer"))


def _tests():
    return section(7, "Tests", items(["Insulation resistance of every circuit.", "Continuity of the protective conductors and equipotential connections.", "Earth fault loop impedance at the far end of the circuits.",
                                      "Operation of the residual current devices.", "Earth electrode resistance."]),
                   gap("test values and instruments: take them from the norm clause once the norm records are reviewed", "engineer of record"))


def _acceptance(context):
    limits = ((context.results.get(6).outputs.get("voltage_drop") or {}).get("limits_pct") or {}) if context.results.get(6) else {}
    return section(8, "Acceptance criteria", paragraph("The maximum voltage drop of each kind of circuit is the one the calculation used:"), table(["kind of circuit", "limit (%)"], sorted(limits.items())),
                   paragraph("An item is accepted when its test passes and its record is delivered."))


def _documentation(context, docs):
    names = sorted(docs)
    files = [f["path"] for f in (context.results.get(10).outputs.get("files") if context.results.get(10) else [])]
    return section(9, "Technical documentation", paragraph("The issue includes these documents and drawings; the contractor delivers the as-built version of each."), items(names), items(files))


def _responsibilities():
    return section(10, "Responsibilities of the contractor", items(["Builds the installation as issued and answers for the quality of the work and the materials.", "Reports any conflict between the drawings and the site before building."]),
                   gap("contractor, insurance and warranty period", "client"))


def _reception():
    return section(11, "Provisional and final reception", items(["Provisional reception follows the passed tests and the delivery of the as-built documents.", "Final reception follows the warranty period."]),
                   gap("warranty period and conditions of reception", "client"))


def build(context, docs):
    """The draft specification of the run. `docs`: the documents of the stage, by name, with the cable list among them."""
    rows = docs["cable_list"]["rows"]
    site = _site(context)
    sections = [_objective(site), _scope(context, rows), _memo(site, context), _norms(site), _conditions(), _technical(context, rows), _tests(), _acceptance(context), _documentation(context, docs),
                _responsibilities(), _reception()]
    gaps = [{"section": s["id"], "text": b["text"], "who": b["who"]} for s in sections for b in s["blocks"] if b["type"] == "gap"]
    return {"document": "specification", "status": "draft", "structure": STRUCTURE, "sections": copy.deepcopy(sections), "gaps": gaps}
