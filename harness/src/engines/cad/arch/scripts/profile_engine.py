"""Where the time of one plan goes: python scripts/profile_engine.py PLAN [--top 15]. Prints the seconds of the whole reading and the functions that took most (cumulative)."""
import argparse
import cProfile
import io
import pstats
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from epc_arch import Options                                                          # noqa: E402
from epc_arch.pipeline import recognize_sheet                                          # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--top", type=int, default=15)
    a = ap.parse_args(argv)
    path = Path(a.plan)
    prof = cProfile.Profile()
    t0 = time.time()
    prof.enable()
    sheet = recognize_sheet(path.read_bytes(), path.name, Options(background=False))
    prof.disable()
    print(f"{path.name}: {time.time() - t0:.1f} s, {len(sheet.levels)} plan(s)")
    out = io.StringIO()
    pstats.Stats(prof, stream=out).sort_stats("cumulative").print_stats(a.top)
    print(out.getvalue())
    return 0


if __name__ == "__main__":
    sys.exit(main())
