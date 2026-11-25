"""DXF output of the platform's drawings: the catalog of layers they are delivered with."""
__version__ = "0.1.0"

__all__ = ["DxfError", "verify", "Stamp", "new_document", "aci_hex", "add_logo_layer", "add_styles", "apply", "by_discipline", "config_dir", "convert", "defaults", "deliver", "describe", "describe_layers", "describe_dxf", "disciplines", "dump", "finish_draft", "get", "get_section", "inspect", "layers_used", "load", "load_file", "logo_layer_name", "moment_of", "name", "new", "new_layer_name", "override_of", "parse", "pin", "resolve", "role_attribute", "save", "sort_classes", "tag_iram_sheet", "unify", "validate"]


def __getattr__(name):
    """The public names load on first use (PEP 562), so importing the package stays as cheap as it was."""
    if name in __all__:
        from epc_draw.core import api
        return getattr(api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
