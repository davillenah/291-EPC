"""The tests of the harness check the strict behaviour: they run in `production` mode unless a test asks for another one.

The default mode of a run comes from `harness/config/default_run_mode` (`edit` on `dev`, `production` on `main`, ADR-0035); pinning `EPC_RUN_MODE` here makes the suite give the same results on both. The tests of the
default itself clear the variable.
"""
import os

os.environ.setdefault("EPC_RUN_MODE", "production")
