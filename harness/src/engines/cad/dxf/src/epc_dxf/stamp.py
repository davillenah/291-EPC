"""Deterministic DXF files: an optional stamp date (and seed) that replaces the clock and the random GUIDs ezdxf writes (MIG-3Z).

ezdxf stamps every file it writes: `$TDCREATE`/`$TDUPDATE` (Julian dates of "now"), `$VERSIONGUID`/`$FINGERPRINTGUID` (random) and the two marker strings of its
metadata dictionary (`CREATED_BY_EZDXF`, `WRITTEN_BY_EZDXF`, "<version> @ <now>"), and the CLASS records are in the order of a `set`. `Drawing.saveas` renews the update time and the version GUID on every write, so setting the
header once is not enough: `save` pins the values again inside the write. Without a stamp nothing here changes the file: `save(doc, path)` is `doc.saveas(path)`.

Checked against ezdxf 1.4.x (`Drawing._update_metadata`); the tests of this engine fail if a newer ezdxf stamps something else.
"""
import datetime
import uuid
from dataclasses import dataclass
from typing import Optional, Union

import ezdxf
from ezdxf.document import CREATED_BY_EZDXF, WRITTEN_BY_EZDXF
from ezdxf.tools import juliandate
from epc_dxf.errors import DxfError

NAMESPACE = uuid.UUID("5d0d1c6e-0291-4e6b-9a47-8c1f5f3a1b10")  # fixed: the GUIDs are uuid5 of (kind, moment, seed) under it
DateLike = Union[str, datetime.date, datetime.datetime, None]


@dataclass(frozen=True)
class Stamp:
    """The moment written as creation and update time, and the seed the GUIDs are derived from (the same drawing name gives the same GUIDs)."""
    moment: datetime.datetime
    seed: str = ""

    def guid(self, kind: str) -> str:
        return "{" + str(uuid.uuid5(NAMESPACE, f"{kind}|{self.moment.isoformat()}|{self.seed}")).upper() + "}"

    def marker(self) -> str:
        return f"{ezdxf.__version__} @ {self.moment.replace(tzinfo=datetime.timezone.utc).isoformat()}"


def moment_of(value: DateLike) -> Optional[datetime.datetime]:
    """An ISO date or datetime (text, `date` or `datetime`) as a naive UTC datetime; a date is midnight. None stays None. Anything else is a ValueError."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        moment = value
    elif isinstance(value, datetime.date):
        moment = datetime.datetime(value.year, value.month, value.day)
    elif isinstance(value, str):
        moment = datetime.datetime.fromisoformat(value.strip())
    else:
        raise DxfError("err_stamp_date_type", type_name=type(value).__name__)
    if moment.tzinfo is not None:
        moment = moment.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return moment


def parse(stamp_date: DateLike, seed: Optional[str] = None) -> Optional[Stamp]:
    """The stamp for a date and a seed, or None when no date is given (the writer then behaves as it always did)."""
    moment = moment_of(stamp_date)
    return None if moment is None else Stamp(moment, "" if seed is None else str(seed))


def pin(doc, stamp: Stamp) -> None:
    """Write the stamp into the header variables and the metadata of an ezdxf document."""
    julian = juliandate(stamp.moment)
    for var in ("$TDCREATE", "$TDUCREATE", "$TDUPDATE", "$TDUUPDATE"):
        doc.header[var] = julian
    doc.header["$FINGERPRINTGUID"] = stamp.guid("fingerprint")
    doc.header["$VERSIONGUID"] = stamp.guid("version")
    meta = doc.ezdxf_metadata()
    meta[CREATED_BY_EZDXF] = stamp.marker()
    meta[WRITTEN_BY_EZDXF] = stamp.marker()


def sort_classes(doc) -> None:
    """Put the CLASSES section in name order. ezdxf appends the classes of the entity types in use by iterating a `set` of strings, whose order changes with every Python process
    (hash randomization), so two identical drawings would differ in the order of two CLASS records."""
    classes = doc.classes.classes
    ordered = sorted(classes.items(), key=lambda item: str(item[0]))
    classes.clear()
    classes.update(ordered)


def new(version: str = "R2010", stamp: Optional[Stamp] = None):
    """`ezdxf.new(version)`, with the stamp pinned when one is given."""
    doc = ezdxf.new(version)
    if stamp is not None:
        pin(doc, stamp)
    return doc


def new_document(version: str = "R2018", *, setup: bool = False, stamp: Optional[Stamp] = None):
    """The one way the engines create a DXF document (OPT-02, drawing base stage 2): `ezdxf.new(version, setup=setup)`, with the stamp pinned when one is given.
    Every engine asks for its document here, so a change to how a drawing starts (units, styles, the stamp) is made once."""
    doc = ezdxf.new(version, setup=setup)
    if stamp is not None:
        pin(doc, stamp)
    return doc


def save(doc, path, stamp: Optional[Stamp] = None) -> None:
    """`doc.saveas(path)`; with a stamp the pinned values are written (ezdxf renews them inside the write, so they are put back right after it does)."""
    if stamp is None:
        doc.saveas(path)
        return
    pin(doc, stamp)
    renew = doc._update_metadata

    def pinned() -> None:
        renew()
        pin(doc, stamp)
        sort_classes(doc)

    doc._update_metadata = pinned
    try:
        doc.saveas(path)
    finally:
        del doc._update_metadata


def document(path, doc=None):
    """The drawing to work on: the one the caller already holds, or the file read once (COD-07)."""
    import ezdxf
    return doc if doc is not None else ezdxf.readfile(str(path))


def save_if(doc, path, stamp: Optional[Stamp] = None, write: bool = True) -> None:
    """`save`, unless the caller keeps working on the same document and writes it at the end."""
    if write:
        save(doc, path, stamp)
