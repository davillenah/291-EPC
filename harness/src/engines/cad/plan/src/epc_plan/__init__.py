"""plan: see MODULE.md and SPEC.md."""
__version__ = "0.1.0"

__all__ = ["PlanError", "area", "best_layout", "build_graph", "cable_mm", "chain", "check", "cut", "default_rules", "derive_inverts", "detect", "dimension_points", "footprints", "gap_3d", "geometry_of", "group_of", "groups", "height_gap", "inside", "isometric", "load_params", "load_profile", "load_rules", "merge", "merge_rules", "mesh", "metres_per_unit", "orient_from_outlet", "parse_level", "partitions", "parts", "plan_gap", "process", "profiles", "propose_runs", "propose_wiring", "reload_params", "room_of", "rule_for", "rule_key", "scene", "size_container", "size_containers", "solids", "split_evenly", "supports", "takeoff", "to_world", "versions", "write_dxf", "write_dxf_3d", "write_obj", "write_section_dxf"]


def __getattr__(name):
    """The public names load on first use (PEP 562), so importing the package stays as cheap as it was."""
    if name in __all__:
        from epc_plan import api
        return getattr(api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
