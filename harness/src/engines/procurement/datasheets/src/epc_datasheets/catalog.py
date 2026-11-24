"""The manufacturer catalog: validation of the documents given as an argument, and the one explicit I/O function `load_catalog_dir`.

Shapes understood (the same as `harness/schemas/manufacturer_catalog.schema.json`):
- manufacturer file `manufacturer.json`: `{"id", "name", "categories": [...], "country"?, "web"?}`
- product file `breakers.json` / `cables.json`: `{"manufacturer", "category", "products": [product, ...]}`; a product has `id, family, type, status, source`
  and optionally `rated_current_a` (`{"min"?, "max"?}`, or a list of numbers), `poles` (list of integers), `breaking_capacity`
  (`[{"voltage_v", "icu_ka", "class"?, "standard"?}]`), `voltage`, `standards`, `construction`, `temperature_c`, `notes`.
The catalog argument is a list of product-file documents; `load_catalog_dir` also adds `manufacturer_name` from the manufacturer file.
"""
import json
import math
from pathlib import Path
from epc_datasheets.errors import DatasheetsError

PRODUCT_FILES = ("breakers.json", "cables.json")
REQUIRED_PRODUCT = ("id", "family", "type", "status", "source")
STATUSES = ("unverified", "verified")
COPIED = ("family", "type", "status", "source", "rated_current_a", "poles", "breaking_capacity", "voltage", "standards", "construction", "temperature_c", "notes")


def _finite(value, where, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
        raise DatasheetsError("err_not_finite_number", where=where, minimum=minimum, value=value)
    return value


def _rated_current(value, where):
    if isinstance(value, list):
        for n in value:
            _finite(n, f"{where}: rated_current_a entry")
    elif isinstance(value, dict):
        unknown = sorted(set(value) - {"min", "max"})
        if unknown:
            raise DatasheetsError("err_rated_current_unknown_keys", where=where, keys=', '.join(unknown))
        for key, n in value.items():
            _finite(n, f"{where}: rated_current_a.{key}")
        if "min" in value and "max" in value and value["min"] > value["max"]:
            raise DatasheetsError("err_rated_current_range", where=where)
    else:
        raise DatasheetsError("err_rated_current_shape", where=where)


def _breaking_capacity(value, where):
    if not isinstance(value, list):
        raise DatasheetsError("err_breaking_capacity_not_list", where=where)
    for n, entry in enumerate(value, start=1):
        if not isinstance(entry, dict) or "voltage_v" not in entry or "icu_ka" not in entry:
            raise DatasheetsError("err_breaking_capacity_entry", where=where, n=n)
        _finite(entry["voltage_v"], f"{where}: breaking_capacity entry {n} voltage_v", 1e-12)
        _finite(entry["icu_ka"], f"{where}: breaking_capacity entry {n} icu_ka", 1e-12)


def _poles(value, where):
    if not isinstance(value, list) or not all(isinstance(p, int) and not isinstance(p, bool) and 1 <= p <= 4 for p in value):
        raise DatasheetsError("err_poles_list", where=where)


def _product(product, where):
    if not isinstance(product, dict):
        raise DatasheetsError("err_product_not_object", where=where)
    missing = [k for k in REQUIRED_PRODUCT if not isinstance(product.get(k), str) or not product[k].strip()]
    if missing:
        raise DatasheetsError("err_missing_keys", where=where, keys=', '.join(missing))
    where = f"{where} product {product['id']}"
    if product["status"] not in STATUSES:
        raise DatasheetsError("err_status_invalid", where=where, allowed=', '.join(STATUSES), got=product['status'])
    checks = {"rated_current_a": _rated_current, "breaking_capacity": _breaking_capacity, "poles": _poles}
    for key, check in checks.items():
        if key in product:
            check(product[key], where)


def _document(doc, n):
    where = f"catalog document {n}"
    if not isinstance(doc, dict):
        raise DatasheetsError("err_not_object", where=where)
    for key in ("manufacturer", "category"):
        if not isinstance(doc.get(key), str) or not doc[key].strip():
            raise DatasheetsError("err_missing_key", where=where, key=key)
    if not isinstance(doc.get("products"), list):
        raise DatasheetsError("err_products_not_list", where=where)
    where = f"{where} ({doc['manufacturer']}/{doc['category']})"
    for product in doc["products"]:
        _product(product, where)
    return where


def products(catalog):
    """Validate the catalog and return its products flattened and sorted by (manufacturer, family, id).

    Each entry is `{"manufacturer", "manufacturer_name"?, "category", "id", ...the copied catalog fields present}`. Duplicate product ids are rejected.
    """
    if not isinstance(catalog, (list, tuple)):
        raise DatasheetsError("err_catalog_invalid")
    flat, seen = [], set()
    for n, doc in enumerate(catalog, start=1):
        _document(doc, n)
        for p in doc["products"]:
            if p["id"] in seen:
                raise DatasheetsError("err_duplicate_product", product_id=p['id'])
            seen.add(p["id"])
            entry = {"manufacturer": doc["manufacturer"], "category": doc["category"], "id": p["id"]}
            if "manufacturer_name" in doc:
                entry["manufacturer_name"] = doc["manufacturer_name"]
            entry.update({k: p[k] for k in COPIED if k in p})
            flat.append(entry)
    return sorted(flat, key=lambda p: (p["manufacturer"], p["family"], p["id"]))


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise DatasheetsError("err_cannot_read", path=path, exc=exc) from exc
    except ValueError as exc:
        raise DatasheetsError("err_invalid_json", path=path, exc=exc) from exc


def _manufacturer(folder):
    info = _read_json(folder / "manufacturer.json") if (folder / "manufacturer.json").is_file() else None
    if info is None:
        raise DatasheetsError("err_no_manufacturer_json", folder=folder)
    for key in ("id", "name"):
        if not isinstance(info, dict) or not isinstance(info.get(key), str) or not info[key].strip():
            raise DatasheetsError("err_missing_key", where=folder / 'manufacturer.json', key=key)
    if not isinstance(info.get("categories"), list) or not info["categories"]:
        raise DatasheetsError("err_categories_empty", where=folder / 'manufacturer.json')
    return info


def _documents(folder, info):
    docs = []
    for name in PRODUCT_FILES:
        path = folder / name
        if not path.is_file():
            continue
        doc = _read_json(path)
        if not isinstance(doc, dict) or doc.get("manufacturer") != info["id"]:
            raise DatasheetsError("err_manufacturer_mismatch", path=path, info=info['id'])
        docs.append(dict(doc, manufacturer_name=info["name"]))
    if not docs:
        raise DatasheetsError("err_no_product_file", folder=folder, names=', '.join(PRODUCT_FILES))
    return docs


def load_catalog_dir(path):
    """Read a catalog folder (`<path>/<manufacturer>/{manufacturer,breakers,cables}.json`) into the `catalog` argument; ValueError when invalid.

    The only I/O of the engine: it is called only when the caller passes a folder. The result is validated (see `products`).
    """
    root = Path(path)
    if not root.is_dir():
        raise DatasheetsError("err_catalog_folder_missing", root=root)
    folders = sorted(p for p in root.iterdir() if p.is_dir())
    if not folders:
        raise DatasheetsError("err_catalog_folder_empty", root=root)
    catalog = []
    for folder in folders:
        catalog += _documents(folder, _manufacturer(folder))
    products(catalog)
    return catalog
