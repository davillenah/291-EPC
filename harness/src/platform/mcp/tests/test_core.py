import io
import json
import tempfile
import unittest
from pathlib import Path

from epc_mcp import guard, protocol
from epc_mcp.envelope import ToolError, ok
from epc_mcp.registry import Context, Registry, Tool


def make_root():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    (root / "ACME" / "P001").mkdir(parents=True)
    return tmp, root


def echo(ctx, args):
    return {"folder": ctx.project(args).name, "n": args.get("n", 0)}


def boom(ctx, args):
    raise RuntimeError("bad")


def refuse(ctx, args):
    raise ToolError("nope", "refused")


def build():
    reg = Registry()
    reg.register(Tool("echo", "echo", echo, {"project": {"type": "string"}}))
    reg.register(Tool("boom", "boom", boom))
    reg.register(Tool("refuse", "refuse", refuse))
    reg.register(Tool("writer", "writer", echo, profiles=("full",)))
    return reg


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.root = make_root()
        self.addCleanup(self.tmp.cleanup)

    def test_project_dir(self):
        self.assertEqual(guard.project_dir(self.root, "ACME/P001").name, "P001")

    def test_bad_project_ids(self):
        for bad in ("", None, "ACME", "ACME/P001/x", "../ACME/P001", "ACME/..", "ACME/NOPE"):
            with self.assertRaises(ToolError, msg=str(bad)):
                guard.project_dir(self.root, bad)

    def test_write_inside(self):
        d = guard.project_dir(self.root, "ACME/P001")
        for sub in ("workspace/a.json", "deliverables/x/y.pdf", ".epc/ledger/l.jsonl", "workspace"):
            self.assertTrue(str(guard.check_write(d, sub)).startswith(str(d.resolve())))

    def test_write_outside(self):
        d = guard.project_dir(self.root, "ACME/P001")
        for bad in ("meta.json", "../P002/workspace/a", "workspace/../meta.json", str(self.root / "x.txt"), "workspaceX/a"):
            with self.assertRaises(ToolError) as cm:
                guard.check_write(d, bad)
            self.assertEqual(cm.exception.code, "forbidden_path")


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.root = make_root()
        self.addCleanup(self.tmp.cleanup)
        self.reg = build()

    def ctx(self, profile="full"):
        return Context(self.root, profile)

    def test_ok_is_wrapped(self):
        r = self.reg.call("echo", {"project": "ACME/P001", "n": 2}, self.ctx())
        self.assertTrue(r["ok"])
        self.assertEqual(r["data"], {"folder": "P001", "n": 2})
        self.assertEqual(r["warnings"], [])

    def test_errors_never_raise(self):
        self.assertEqual(self.reg.call("boom", {"project": "ACME/P001"}, self.ctx())["error"]["code"], "internal_error")
        self.assertEqual(self.reg.call("refuse", {"project": "x"}, self.ctx())["error"]["code"], "nope")
        self.assertEqual(self.reg.call("echo", {}, self.ctx())["error"]["code"], "invalid_arguments")
        self.assertEqual(self.reg.call("missing", {}, self.ctx())["error"]["code"], "unknown_tool")
        self.assertEqual(self.reg.call("echo", {"project": "ACME/NOPE"}, self.ctx())["error"]["code"], "project_not_found")

    def test_readonly_profile(self):
        self.assertNotIn("writer", self.reg.names("readonly"))
        r = self.reg.call("writer", {"project": "ACME/P001"}, self.ctx("readonly"))
        self.assertEqual(r["error"]["code"], "unknown_tool")

    def test_duplicate_tool(self):
        with self.assertRaises(ValueError):
            self.reg.register(Tool("echo", "again", echo))

    def test_envelope_passthrough_and_extras(self):
        reg = Registry()
        reg.register(Tool("e", "e", lambda c, a: ok({"v": 1}, ["w"], reason="r", confidence="high"), required=[]))
        r = reg.call("e", None, self.ctx())
        self.assertEqual((r["warnings"], r["reason"], r["confidence"]), (["w"], "r", "high"))


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.root = make_root()
        self.addCleanup(self.tmp.cleanup)

    def run_lines(self, messages, profile="full"):
        out = io.StringIO()
        raw = "\n".join(m if isinstance(m, str) else json.dumps(m) for m in messages) + "\n"
        protocol.serve(build(), Context(self.root, profile), io.StringIO(raw), out)
        return [json.loads(x) for x in out.getvalue().splitlines()]

    def test_handshake_and_list(self):
        res = self.run_lines([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "ping"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
        ])
        self.assertEqual([r["id"] for r in res], [1, 2, 3])
        self.assertEqual(res[0]["result"]["serverInfo"]["name"], "epc")
        names = [t["name"] for t in res[2]["result"]["tools"]]
        self.assertEqual(names, sorted(names))
        self.assertIn("echo", names)

    def test_readonly_list(self):
        res = self.run_lines([{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}], "readonly")
        self.assertNotIn("writer", [t["name"] for t in res[0]["result"]["tools"]])

    def test_call(self):
        res = self.run_lines([{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                               "params": {"name": "echo", "arguments": {"project": "ACME/P001"}}},
                              {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "boom", "arguments": {"project": "ACME/P001"}}}])
        body = json.loads(res[0]["result"]["content"][0]["text"])
        self.assertTrue(body["ok"])
        self.assertFalse(res[0]["result"]["isError"])
        self.assertTrue(res[1]["result"]["isError"])

    def test_malformed_calls_keep_serving(self):
        call = {"jsonrpc": "2.0", "method": "tools/call"}
        res = self.run_lines([
            dict(call, id=1, params=[1]),
            dict(call, id=2, params="x"),
            dict(call, id=3, params={"name": [1]}),
            dict(call, id=4, params={"name": "echo", "arguments": 5}),
            dict(call, id=5, params={"name": "echo", "arguments": "project"}),
            {"jsonrpc": "2.0", "id": 6, "method": ["x"]},
            {"jsonrpc": "2.0", "id": 7, "method": "ping"},
        ])
        self.assertEqual([r["id"] for r in res], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(res[0]["error"]["code"], -32602)
        self.assertEqual(res[1]["error"]["code"], -32602)
        for r in res[2:5]:
            self.assertTrue(r["result"]["isError"])
        self.assertEqual(res[5]["error"]["code"], -32602)
        self.assertEqual(res[6]["result"], {})

    def test_unserializable_and_non_ascii(self):
        reg = Registry()
        reg.register(Tool("odd", "odd", lambda c, a: {"s": {1, 2}, "t": "ñandú"}, required=[]))
        out = io.StringIO()
        msg = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "odd"}}
        protocol.serve(reg, Context(self.root), io.StringIO(json.dumps(msg) + "\n"), out)
        out.getvalue().encode("ascii")  # stays ASCII-safe on any stdout encoding
        self.assertFalse(json.loads(out.getvalue())["result"]["isError"])

    def test_trailing_dot_project(self):
        with self.assertRaises(ToolError):
            guard.project_dir(self.root, "ACME/P001.")

    def test_protocol_errors(self):
        res = self.run_lines(["not json", {"jsonrpc": "2.0", "id": 5, "method": "nope"}, {"id": 6}, ""])
        self.assertEqual(res[0]["error"]["code"], -32700)
        self.assertEqual(res[1]["error"]["code"], -32601)
        self.assertEqual(res[2]["error"]["code"], -32600)


if __name__ == "__main__":
    unittest.main()
