"""PJM metered hourly load -> DOM and PJM-RTO series.

Two traps this handles:
  1. Rows are per load_area, several per zone, so they must be aggregated.
  2. A pseudo-zone `RTO` carries the system total. Summing all zones INCLUDING
     it double-counts (~285,000 MW against a real PJM record near 165,000).
     We take the RTO row directly instead.
"""
from __future__ import annotations
import glob
import pandas as pd
from config import P_LOAD, LOAD_ZONES, PJM_DT_FMT
import qa

USE = ["datetime_beginning_utc", "zone", "load_area", "mw"]


def run() -> pd.DataFrame:
    files = sorted(glob.glob(str(P_LOAD / "*.csv")))
    if not files:
        raise FileNotFoundError(f"no CSVs in {P_LOAD}")

    parts, rows_in = [], 0
    for f in files:
        d = pd.read_csv(f, usecols=USE, low_memory=False)
        rows_in += len(d)
        parts.append(d[d["zone"].isin(LOAD_ZONES)])
    df = pd.concat(parts, ignore_index=True)

    df["datetime_utc"] = pd.to_datetime(df["datetime_beginning_utc"], format=PJM_DT_FMT)
    df["mw"] = pd.to_numeric(df["mw"], errors="coerce")

    # overlapping year exports repeat boundary hours; keep one row per area-hour
    before = len(df)
    df = df.drop_duplicates(subset=["datetime_utc", "zone", "load_area"], keep="last")
    dupes = before - len(df)

    wide = (df.groupby(["datetime_utc", "zone"])["mw"].sum()
              .unstack("zone")
              .rename(columns={"DOM": "dom_load_mw", "RTO": "pjm_rto_load_mw"})
              .sort_index()
              .reset_index())
    for c in ("dom_load_mw", "pjm_rto_load_mw"):
        if c not in wide:
            wide[c] = pd.NA
    wide = wide[["datetime_utc", "dom_load_mw", "pjm_rto_load_mw"]]

    wide, notes = qa.apply_bounds(wide)
    notes.append("zone rows aggregated from load_area level")
    notes.append("pseudo-zone 'RTO' taken directly as the system total, not summed with zones")
    if dupes:
        notes.append(f"{dupes:,} duplicate area-hours removed (overlapping year exports)")
    notes.append(f"span {wide.datetime_utc.min():%Y-%m-%d} to {wide.datetime_utc.max():%Y-%m-%d}")

    qa.record("load (PJM metered)", sources=files, rows_in=rows_in,
              rows_out=len(wide), notes=notes)
    qa.write(wide, "pjm_load_hourly.csv")
    return wide


if __name__ == "__main__":
    run()
