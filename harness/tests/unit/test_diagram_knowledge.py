"""Diagram knowledge (harness/knowledge/diagrams): every JSON validates against its schema, nothing is "verified", and the bridge to the symbol library is consistent (symbol ids and ports exist in the library catalogs, device ids exist)."""
import glob
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator as V

H = Path(__file__).resolve().parents[2]
K = H / "knowledge" / "diagrams"
LIB = H / "src" / "engines" / "cad" / "symbols" / "src" / "epc_symbols" / "library"
PAIRS = [("sld_mld/devices", "sld_mld/schema/device.schema.json"), ("sld_mld/schemes", "sld_mld/schema/scheme.schema.json"),
         ("pv_sld_mld/devices", "pv_sld_mld/schema/pv_sld_mld.schema.json"), ("pv_sld_mld/schemes", "pv_sld_mld/schema/pv_sld_mld.schema.json"),
         ("funcional_iec60617/symbols", "funcional_iec60617/symbol.schema.json"), ("funcional_iec60617/circuits", "funcional_iec60617/circuit.schema.json"),
         ("pv_funcional/circuits", "pv_funcional/pv_circuit.schema.json"), ("puente_motor_dibujo/netlists", "puente_motor_dibujo/netlist.schema.json")]


def catalog():
    ports = {}
    for lib in ("sld-lv-symbol", "mld-lv-symbol", "sld-mv-symbol"):
        for s in json.loads((LIB / lib / "_catalog.json").read_text(encoding="utf-8-sig"))["symbols"]:
            ports[s["id"]] = [p["id"] for p in s.get("ports", [])]
    return ports


class DiagramKnowledge(unittest.TestCase):
    def test_schemas_and_no_verified(self):
        n = 0
        for d, s in PAIRS:
            v = V(json.loads((K / s).read_text(encoding="utf-8")))
            for f in sorted(glob.glob(str(K / d / "*.json"))):
                if "index" in f:
                    continue
                text = Path(f).read_text(encoding="utf-8")
                n += 1
                self.assertEqual([], [e.message for e in v.iter_errors(json.loads(text))], f)
                self.assertNotIn('"verified"', text, f)
        self.assertGreater(n, 100)

    def test_symbol_map_matches_library_and_devices(self):
        cat = catalog()
        devs = {Path(f).stem for d in ("sld_mld/devices", "pv_sld_mld/devices") for f in glob.glob(str(K / d / "*.json"))}
        m = json.loads((K / "puente_motor_dibujo/device_symbol_map.json").read_text(encoding="utf-8"))["mappings"]
        self.assertEqual(devs, {x["device_id"] for x in m})
        from epc_drawing import diagram_knowledge as DK
        for x in m:
            self.assertNotIn("ports", x)          # one source (COD-03): ports and MLD variants come from the symbol catalogue
            self.assertNotIn("mld_symbols", x)
            if x["sld_symbol"] is None:
                self.assertEqual("not_found", x["status"])
                self.assertEqual({"ports": [], "mld_symbols": []}, {k: DK.symbol_for(x["device_id"])[k] for k in ("ports", "mld_symbols")})
                continue
            got = DK.symbol_for(x["device_id"])
            self.assertEqual(cat[x["sld_symbol"]], got["ports"], x["device_id"])
            for mld in got["mld_symbols"]:
                self.assertIn(mld, cat)

    def test_netlists_use_existing_symbols_ports_and_devices(self):
        cat = catalog()
        devs = {Path(f).stem for d in ("sld_mld/devices", "pv_sld_mld/devices") for f in glob.glob(str(K / d / "*.json"))}
        for f in glob.glob(str(K / "puente_motor_dibujo/netlists/*.json")):
            nl = json.loads(Path(f).read_text(encoding="utf-8"))
            sym = {i["tag"]: i["symbol"] for i in nl["instances"]}
            self.assertEqual(len(sym), len(nl["instances"]), f)
            for i in nl["instances"]:
                if "source_scheme" in nl:
                    self.assertIn(i["device_id"], devs, f)
                if i["symbol"] is not None:
                    self.assertIn(i["symbol"], cat, f)
            for c in nl["connections"]:
                for end in (c["from"], c["to"]):
                    tag, port = end.split(":")
                    self.assertIn(port, cat[sym[tag]], f"{f} {end}")

    def test_relational_model_examples(self):
        """devices.json, loads.json, wires.json and circuits.json link only by unique ids; every reference, symbol and port exists; wires carry no values."""
        cat = catalog()
        devs = {Path(f).stem for d in ("sld_mld/devices", "pv_sld_mld/devices") for f in glob.glob(str(K / d / "*.json"))}
        base = K / "puente_motor_dibujo/model"
        schemas = {n: V(json.loads((base / f"{n}.schema.json").read_text(encoding="utf-8"))) for n in ("devices", "loads", "wires", "circuits")}
        examples = sorted(p for p in (base / "examples").iterdir() if p.is_dir())
        self.assertGreaterEqual(len(examples), 4)
        for ex in examples:
            data = {}
            for n, v in schemas.items():
                data[n] = json.loads((ex / f"{n}.json").read_text(encoding="utf-8"))
                self.assertEqual([], [e.message for e in v.iter_errors(data[n])], str(ex / n))
            nodes = {d["id"]: d for d in data["devices"]["devices"]}
            nodes.update({x["id"]: x for x in data["loads"]["loads"]})
            self.assertEqual(len(nodes), len(data["devices"]["devices"]) + len(data["loads"]["loads"]), f"duplicate id in {ex.name}")
            for d in data["devices"]["devices"]:
                self.assertIn(d["device_id"], devs, ex.name)
                self.assertIn(d["symbol"], cat, ex.name)
            for x in data["loads"]["loads"]:
                self.assertIn(x["symbol"], cat, ex.name)
            wires = {w["id"]: w for w in data["wires"]["wires"]}
            self.assertEqual(len(wires), len(data["wires"]["wires"]), ex.name)
            for w in wires.values():
                for end in (w["from"], w["to"]):
                    self.assertIn(end["ref"], nodes, ex.name)
                    self.assertIn(end["port"], cat[nodes[end["ref"]]["symbol"]], f"{ex.name} {w['id']}")
            for c in data["circuits"]["circuits"]:
                self.assertTrue(set(c["wires"]) <= set(wires), ex.name)
                self.assertTrue(c["load"] is None or c["load"] in nodes, ex.name)


if __name__ == "__main__":
    unittest.main()
