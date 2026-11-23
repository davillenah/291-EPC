"""The tests of the harness check the strict behaviour: they run in `production` mode unless a test asks for another one.

The default mode of a run comes from `harness/config/default_run_mode` (`edit` on `dev`, `production` on `main`, ADR-0035); pinning `EPC_RUN_MODE` here makes the suite give the same results on both. The tests of the
default itself clear the variable.
"""
import os

os.environ.setdefault("EPC_RUN_MODE", "production")


# COD-14: the modules that run whole pipelines (several seconds per test) carry the `slow` marker, so a quick loop can run
# `python -m pytest harness/tests -m "not slow"`. The gate and the CI run everything: nothing is skipped there.
SLOW_MODULES = {"test_building_intake", "test_model3d_stage", "test_pv_stage", "test_spike_dry_run_fresh", "test_cli_parity",
                "test_reproducibility", "test_resume", "test_synthetic_lv_small", "test_synthetic_permissions"}


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: runs a whole pipeline (seconds per test); leave out with -m 'not slow'")


def pytest_collection_modifyitems(items):
    import pytest
    for item in items:
        if item.module.__name__.rsplit(".", 1)[-1] in SLOW_MODULES:
            item.add_marker(pytest.mark.slow)
