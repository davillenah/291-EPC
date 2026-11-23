"""One reader per kind of source. A reader adapts a file to the primitives the recognizers understand; the registry picks the reader from what the caller says or from the bytes.
A new source is a new module here that registers itself: nothing that recognizes changes."""
from typing import Dict, Protocol

from epc_arch.model import ArchError, Options, Primitives


class Reader(Protocol):
    kind: str

    def read(self, data: bytes, options: Options) -> Primitives: ...


_READERS: Dict[str, Reader] = {}


def register(cls):
    """Class decorator: make a reader available under its `kind`."""
    reader = cls()
    _READERS[reader.kind] = reader
    return cls


def _load() -> None:
    from epc_arch.sources import dxf, pdf, raster, svg  # noqa: F401  (importing them registers the readers)


def kinds() -> list:
    _load()
    return sorted(_READERS)


def _is_image(head: bytes) -> bool:
    return head.startswith((b"\x89PNG", b"\xff\xd8\xff", b"II*\x00", b"MM\x00*", b"BM", b"RIFF"))


def detect_kind(data: bytes, name: str = "") -> str:
    """dxf, pdf or image, from the first bytes (the extension only breaks the tie for a DXF, whose text varies)."""
    head = data[:2048]
    if head.startswith(b"%PDF"):
        return "pdf"
    if _is_image(head):
        return "image"
    text = head.lower()
    if b"<svg" in text or name.lower().endswith(".svg"):
        return "svg"
    if name.lower().endswith(".dxf") or b"section" in text or head.startswith(b"AutoCAD Binary DXF"):
        return "dxf"
    raise ArchError("err_file_kind")


def read(data: bytes, name: str = "", options: Options = Options()) -> Primitives:
    _load()
    kind = options.kind or detect_kind(data, name)
    if kind not in _READERS:
        raise ArchError("err_no_reader", kind=kind, kinds=', '.join(kinds()))
    return _READERS[kind].read(data, options)
