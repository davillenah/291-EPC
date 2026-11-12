"""MIG-33a: the append-only hash-chained event log and the audit trail. Temp folders only; clock and random source are injected."""
import json
import random
import tempfile
import unittest
from pathlib import Path

from epc_platform.audit import AuditTrail
from epc_platform.events import GENESIS, EventLog, EventLogError

ACTOR = {"role": "orchestrator", "id": "o1"}


def clock():
    n = [0]

    def tick():
        n[0] += 1
        return f"2026-01-01T00:00:{n[0]:02d}Z"
    return tick


def event(action="run", result="ok", **extra):
    return dict({"pipeline_run_id": "r1", "actor": ACTOR, "action": action, "target": "ssot/x.json", "result": result, "detail": {"n": 1}}, **extra)


class LogCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.project = Path(self._tmp.name) / "P1"
        (self.project / "audit").mkdir(parents=True)
        self.log = EventLog.for_project(self.project, clock())

    def fill(self, n=4):
        return [self.log.append(event(f"a{i}")) for i in range(n)]

    def lines(self):
        return self.log.path.read_bytes().decode().split("\n")[:-1]

    def rewrite(self, lines):
        self.log.path.write_bytes(("\n".join(lines) + "\n").encode())


class ChainTests(LogCase):
    def test_records_have_the_documented_fields_and_chain(self):
        recs = self.fill(3)
        self.assertEqual([r["seq"] for r in recs], [1, 2, 3])
        self.assertEqual(recs[0]["prev_hash"], GENESIS)
        self.assertEqual(recs[1]["prev_hash"], recs[0]["hash"])
        self.assertEqual(sorted(recs[0]), sorted(["seq", "ts", "pipeline_run_id", "actor", "action", "target", "result", "detail", "prev_hash", "hash"]))
        self.assertEqual(recs[0]["ts"], "2026-01-01T00:00:01Z")
        self.assertEqual(self.log.verify(), [])

    def test_file_is_one_sorted_json_line_per_event_with_lf(self):
        self.fill(2)
        raw = self.log.path.read_bytes()
        self.assertNotIn(b"\r", raw)
        for line in raw.decode().split("\n")[:-1]:
            self.assertEqual(json.dumps(json.loads(line), sort_keys=True, separators=(",", ":")), line)

    def test_an_edited_line_is_found(self):
        self.fill()
        lines = self.lines()
        lines[1] = lines[1].replace('"result":"ok"', '"result":"denied"')
        self.rewrite(lines)
        self.assertEqual([f["line"] for f in self.log.verify()], [2])

    def test_an_edited_line_with_a_recomputed_hash_breaks_the_next_link(self):
        self.fill()
        lines = self.lines()
        rec = json.loads(lines[1])
        rec["action"] = "forged"
        from epc_platform.events.log import hash_of, line_of
        rec["hash"] = hash_of(rec)
        lines[1] = line_of(rec)
        self.rewrite(lines)
        self.assertEqual([f["line"] for f in self.log.verify()], [3])

    def test_a_removed_middle_line_is_found(self):
        self.fill()
        lines = self.lines()
        del lines[1]
        self.rewrite(lines)
        self.assertTrue(self.log.verify())

    def test_reordered_lines_are_found(self):
        self.fill()
        lines = self.lines()
        lines[1], lines[2] = lines[2], lines[1]
        self.rewrite(lines)
        self.assertTrue(self.log.verify())

    def test_a_removed_last_line_is_found_only_with_an_anchor(self):
        recs = self.fill()
        self.rewrite(self.lines()[:-1])
        self.assertEqual(self.log.verify(), [])
        self.assertTrue(self.log.verify(expected_last_hash=recs[-1]["hash"]))
        self.assertTrue(self.log.verify(expected_count=4))

    def test_garbage_and_extra_fields_are_found(self):
        self.fill(2)
        self.rewrite(self.lines() + ["not json"])
        self.assertEqual([f["line"] for f in self.log.verify()], [3])

    def test_appending_continues_the_chain_after_reopening(self):
        self.fill(2)
        again = EventLog.for_project(self.project, clock())
        again.append(event("later"))
        self.assertEqual(again.verify(), [])
        self.assertEqual(again.last()[0], 3)


class ApiTests(LogCase):
    def test_there_is_no_way_to_update_or_delete(self):
        public = {n for n in dir(EventLog) if not n.startswith("_")}
        self.assertEqual(public, {"append", "for_project", "last", "read", "verify"})

    def test_bad_events_are_refused(self):
        for bad in (event(result="maybe"), event(action=""), dict(event(), actor={"role": "x"}), dict(event(), detail=[1]), dict(event(), detail={"x": float("nan")})):
            with self.subTest(bad=bad):
                with self.assertRaises(EventLogError):
                    self.log.append(bad)
        self.assertFalse(self.log.path.exists())

    def test_a_clock_is_required(self):
        with self.assertRaises(EventLogError):
            EventLog(self.log.path, None)

    def test_it_refuses_a_location_outside_the_project_audit_folder(self):
        root = self.project
        for bad in (root / "events.jsonl", root / "ssot" / "events.jsonl", root / "audit" / "other.jsonl", root / "audit" / "sub" / "events.jsonl",
                    root.parent / "events.jsonl", root / "audit" / ".." / "ssot" / "events.jsonl"):
            with self.subTest(bad=str(bad)):
                with self.assertRaises(EventLogError):
                    EventLog(bad, clock(), project_dir=root)

    def test_it_refuses_an_audit_folder_that_leaves_the_project(self):
        import os
        import subprocess
        outside = Path(self._tmp.name) / "elsewhere"
        outside.mkdir()
        other = Path(self._tmp.name) / "P2"
        other.mkdir()
        link = other / "audit"
        try:
            if os.name == "nt":
                subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], check=True, capture_output=True)
            else:
                os.symlink(outside, link)
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("the OS does not allow creating a link here")
        with self.assertRaises(EventLogError):
            EventLog.for_project(other, clock())


class AuditTests(LogCase):
    def trail(self, seed=7):
        return AuditTrail(self.log, clock(), rng=random.Random(seed))

    def test_run_id_is_deterministic_and_valid(self):
        import re
        a, b = self.trail().new_run_id(), self.trail().new_run_id()
        self.assertEqual(a, b)
        self.assertRegex(a, r"^run-20260101T000001Z-[0-9a-f]{8}$")
        self.assertTrue(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", a))
        self.assertNotEqual(a, self.trail(8).new_run_id())

    def test_record_needs_a_run_and_summary_counts(self):
        t = self.trail()
        with self.assertRaises(ValueError):
            t.record(ACTOR, "x", "y", "ok")
        run = t.new_run_id()
        t.record(ACTOR, "run", "ssot", "ok")
        t.record(ACTOR, "run", "ssot", "failed")
        t.record({"role": "calc_check", "id": "c"}, "verify", "ssot", "ok", {"k": 1})
        s = t.summary()
        self.assertEqual((s["pipeline_run_id"], s["events"], s["total_events"]), (run, 3, 3))
        self.assertEqual(s["by_actor"], {"calc_check": 1, "orchestrator": 2})
        self.assertEqual(s["by_action"], {"run": 2, "verify": 1})
        self.assertEqual(s["by_result"], {"failed": 1, "ok": 2})
        self.assertEqual(s["last_hash"], self.log.read()[-1]["hash"])

    def test_two_identical_trails_write_identical_files(self):
        out = []
        for name in ("A", "B"):
            project = Path(self._tmp.name) / name
            log = EventLog.for_project(project, clock())
            t = AuditTrail(log, clock(), rng=random.Random(1))
            t.new_run_id()
            t.record(ACTOR, "run", "ssot", "ok", {"a": 1})
            out.append(log.path.read_bytes())
        self.assertEqual(out[0], out[1])

    def test_empty_summary(self):
        s = self.trail().summary()
        self.assertEqual((s["events"], s["last_hash"]), (0, None))


if __name__ == "__main__":
    unittest.main()
