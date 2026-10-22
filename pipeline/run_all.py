"""Run the whole cleaning pipeline.

    python3 run_all.py            # PJM-based master (authoritative, not publishable)
    python3 run_all.py --public   # EIA-based master as well (publishable)

Raw downloads in ../original_data/ are never modified. Cleaned CSVs are written beside the code.
"""
from __future__ import annotations
import sys, traceback
import qa
from config import CLEAN
import clean_load, clean_lmp, clean_weather, clean_eia930, clean_misc, build_master

STEPS = [
    ("PJM metered load",      clean_load.run),
    ("Day-ahead LMP",         clean_lmp.run),
    ("Weather (METAR)",       clean_weather.run),
    ("EIA-930 load",          clean_eia930.run),
    ("Ancillary reserves",    clean_misc.ancillary),
    ("Regulation prices",     clean_misc.regulation),
    ("NSPL",                  clean_misc.nspl),
    ("Load forecasts",        clean_misc.forecast),
]


def main(public: bool = False):
    print("Cleaning raw sources\n" + "-" * 58)
    failed, skipped = [], []
    for label, fn in STEPS:
        try:
            fn()
        except FileNotFoundError as e:
            print(f"  {label:<22} SKIPPED - {e}")
            skipped.append(label)
        except Exception as e:
            print(f"  {label:<22} FAILED - {type(e).__name__}: {e}")
            traceback.print_exc(limit=2)
            failed.append((label, str(e)))

    print("\nBuilding master panel\n" + "-" * 58)
    # with --public and no PJM load, the PJM build would only repeat the EIA one
    if (CLEAN / "pjm_load_hourly.csv").exists() or not public:
        build_master.run("pjm")
    if public:
        build_master.run("eia")

    report = qa.write_report()
    print(f"\nReport: {report}")
    if skipped:
        print("\nSkipped (raw input not present): " + ", ".join(skipped))
    if failed:
        print("\nIncomplete steps:")
        for label, why in failed:
            print(f"  - {label}: {why}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(public="--public" in sys.argv))
