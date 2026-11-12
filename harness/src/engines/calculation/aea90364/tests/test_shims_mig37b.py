"""MIG-37b: `python -m epc_aea90364.<module>` of the moved modules still works through the shims (the demo blocks and the command line)."""
import subprocess
import sys
import unittest


def _run(module, *args):
    return subprocess.run([sys.executable, "-B", "-m", f"epc_aea90364.{module}", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")


class TestShimsMain(unittest.TestCase):
    def test_the_demo_blocks_still_run_through_the_old_names(self):
        for name in ("cable_thermal", "current_and_loads", "short_circuit", "voltage_drop"):
            with self.subTest(module=name):
                done = _run(name)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertIn("==", done.stdout)

    def test_the_conductor_selection_command_line_still_runs_through_the_old_name(self):
        self.assertNotEqual(_run("conductor_selection", "/no/existe.json").returncode, 0)


if __name__ == "__main__":
    unittest.main()
