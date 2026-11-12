"""Every engine package exposes `__version__`, equal to the version in its pyproject.toml.

The version is what the pipeline records next to each engine call and in the manifests, so an engine without one leaves a number untraceable.
Run: python -m unittest discover -s harness/tests/architecture
"""
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "harness" / "tools"))
sys.path.insert(0, str(REPO / "harness" / "tools" / "build"))
import impact_map as IM  # noqa: E402


class EngineVersions(unittest.TestCase):
    def test_version_in_the_package_equals_the_one_in_pyproject(self):
        for unit in IM.engine_units():
            init = (REPO / IM.ENGINE_ROOTS[unit] / "__init__.py").read_text(encoding="utf-8-sig")
            project = (REPO / IM.PYPROJECT[unit] / "pyproject.toml").read_text(encoding="utf-8")
            in_code = re.search(r'^__version__\s*=\s*"([^"]+)"', init, re.M)
            in_project = re.search(r'^version\s*=\s*"([^"]+)"', project, re.M)
            with self.subTest(engine=unit):
                self.assertIsNotNone(in_code, f"{unit}: __init__.py has no __version__")
                self.assertEqual(in_code.group(1), in_project.group(1))


if __name__ == "__main__":
    unittest.main()
