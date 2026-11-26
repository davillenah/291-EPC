"""The public entry point of the photovoltaic drawings (OPT-02, ADR-0040): `draw_pv(entrada, out_dir, name)`.

One call for the three writers the stage used one by one (`pv_diagrams.write_all` for the ground layout, `pv_roof.write_all` for the roof planes and `pv_details.write` for the equipment detail).
`PvDrawInput` holds the data; nothing is read from the process environment. The writers stay as the lower-level calls, so the drafts are the same bytes."""
import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple


@dataclass(frozen=True)
class PvDrawInput:
    """What the photovoltaic drawings need: any of the layout (ground), the roof placement and the equipment records, plus the yield result they annotate."""
    result: Mapping[str, Any]                       # the yield result of `epc_pv` (stage 3 `outputs["pv"]`)
    layout: Optional[Mapping[str, Any]] = None      # ground layout (`epc_pv.plan_layout`)
    roof: Optional[Mapping[str, Any]] = None        # roof placement
    parts: Optional[Mapping[str, Any]] = None       # equipment records for the detail sheet (None: no detail sheet)
    disk: Optional[Mapping[str, Any]] = None        # irradiation disk data (`epc_pv.disk`, refined by the caller); None: no disk drawing
    abacus: Optional[Mapping[str, Any]] = None      # shading abacus data (`epc_pv.abacus.compute`); None: no abacus drawing
    language: str = "en"
    stamp_date: Optional[str] = None


def draw_pv(entrada: PvDrawInput, out_dir: Any, name: str) -> Tuple[Dict[str, Path], List[str]]:
    """Writes the drafts the input asks for into `<out_dir>/pv_drafts` as `<name>_pv_*` and returns ({draft name: path}, the writers that ran, in order)."""
    if not isinstance(entrada, PvDrawInput):
        raise TypeError("draw_pv() takes a PvDrawInput")
    from epc_draw.pv import details as pv_details, diagrams as pv_diagrams, roof as pv_roof
    target = Path(out_dir) / "pv_drafts"
    stem, drafts, ran = f"{name}_pv", {}, []
    def detail() -> None:
        if entrada.parts is None:
            return
        path = pv_details.write(dict(entrada.parts), target, stem, entrada.language, entrada.stamp_date)
        if path is not None:
            drafts[f"{stem}_equipment_detail"] = path
            ran.append("pv_details.write")

    if entrada.layout is not None:                  # ground layout, then its equipment detail
        drafts.update(pv_diagrams.write_all(copy.deepcopy(dict(entrada.layout)), entrada.result, target, stem, entrada.language, entrada.stamp_date))
        ran.append("pv_diagrams.write_all")
        detail()
    if entrada.roof is not None:                    # roof planes; the detail goes here only when there is no ground layout
        drafts.update(pv_roof.write_all(copy.deepcopy(dict(entrada.roof)), entrada.result, target, stem, entrada.language, entrada.stamp_date))
        ran.append("pv_roof.write_all")
        if entrada.layout is None:
            detail()
    charts = _charts(entrada, stem)                 # irradiation disk and shading abacus
    if charts:
        from epc_draw.pv import files as pv_files
        drafts.update({Path(k).stem: v for k, v in pv_files.save(target, charts).items()})
        ran.append("pv_charts.render")
    return drafts, ran


def _charts(entrada: PvDrawInput, stem: str) -> Dict[str, bytes]:
    """The irradiation disk and the shading abacus, as {file name: DXF bytes}, for the data the input carries."""
    from epc_draw.pv import abacus as pv_abacus, disk as pv_disk
    files: Dict[str, bytes] = {}
    if entrada.disk is not None:
        files.update(pv_disk.render(dict(entrada.disk), stem, entrada.language, "color", entrada.stamp_date))
    if entrada.abacus is not None:
        files.update(pv_abacus.render(dict(entrada.abacus), stem, entrada.language, entrada.stamp_date))
    return files


def render_pv(entrada: PvDrawInput, name: str) -> Dict[str, bytes]:
    """The same drawings as `draw_pv`, as data: {file name: DXF bytes}, in the order the writers run. Nothing is read from the process and nothing is written (ADR-0042):
    two calls with the same input give the same bytes and may run at the same time (give `stamp_date` for the same bytes every time)."""
    if not isinstance(entrada, PvDrawInput):
        raise TypeError("render_pv() takes a PvDrawInput")
    from epc_draw.pv import details as pv_details, diagrams as pv_diagrams, roof as pv_roof
    stem, files = f"{name}_pv", {}
    def detail() -> None:
        if entrada.parts is not None:
            files.update(pv_details.render(dict(entrada.parts), stem, entrada.language, entrada.stamp_date))

    if entrada.layout is not None:
        files.update(pv_diagrams.render_all(copy.deepcopy(dict(entrada.layout)), entrada.result, stem, entrada.language, entrada.stamp_date))
        detail()
    if entrada.roof is not None:
        files.update(pv_roof.render_all(copy.deepcopy(dict(entrada.roof)), entrada.result, stem, entrada.language, entrada.stamp_date))
        if entrada.layout is None:
            detail()
    files.update(_charts(entrada, stem))
    return files
