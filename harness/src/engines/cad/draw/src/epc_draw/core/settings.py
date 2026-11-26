"""The DXF settings a call works with (ADR-0042): where the overrides of the layer catalog and of the text look are, handed in as data and never read from the process.

`DxfSettings` is a frozen value. `use(settings)` makes it the one in force for the calls made inside the `with` block, in the current thread or task only (a `ContextVar`),
so two drawings with different settings can be made at the same time. Without a block the settings are the packaged ones: no override.
`from_environment(environ)` builds the settings from a mapping that the CALLER hands in (the command-line adapter hands `os.environ`); the engine never touches the process environment.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

ENV_LAYERS = "EPC_LAYERS_JSON"
ENV_DIR = "EPC_DXF_CONFIG_DIR"
ENV_TEXT = "EPC_DXF_TEXT_JSON"


@dataclass(frozen=True)
class DxfSettings:
    """`config_dir`: folder with `text.json` and `layers.json` that override the packaged ones (None: the packaged `harness/config/dxf`; "": no folder).
    `layer_files` and `text_files`: override files, later ones winning."""
    config_dir: Optional[str] = None
    layer_files: Tuple[str, ...] = ()
    text_files: Tuple[str, ...] = ()


_NONE = DxfSettings()
_CURRENT: ContextVar[DxfSettings] = ContextVar("epc_dxf_settings", default=_NONE)


def current() -> DxfSettings:
    """The settings in force for this call."""
    return _CURRENT.get()


@contextmanager
def use(settings: DxfSettings):
    """Run the calls inside the block with `settings`."""
    token = _CURRENT.set(settings)
    try:
        yield settings
    finally:
        _CURRENT.reset(token)


def _paths(value: Optional[str], separator: str) -> Tuple[str, ...]:
    return tuple(x for x in (value or "").split(separator) if x)


def from_environment(environ: Mapping[str, str], separator: str) -> DxfSettings:
    """The settings an environment mapping names (`EPC_DXF_CONFIG_DIR`, `EPC_LAYERS_JSON`, `EPC_DXF_TEXT_JSON`); `separator` is the path separator of the system (`os.pathsep`)."""
    return DxfSettings(config_dir=environ.get(ENV_DIR), layer_files=_paths(environ.get(ENV_LAYERS), separator), text_files=_paths(environ.get(ENV_TEXT), separator))
