"""EIA-930 subregion demand -> public-domain DOM and PJM-RTO series.

This is the redistributable substitute for the PJM feed. Validation against
PJM billing-grade data matched 35 of 40 coincident-peak hours with peak-load
contribution within 1% in every year.

Note the clock: EIA-930 timestamps the END of the hour, PJM the BEGINNING.
One hour is subtracted here so both land on the same canonical key.
"""
from __future__ import annotations
import glob
import pandas as pd
from config import P_EIA, EIA_PJM_SUBREGIONS
import qa

USE = ["Balancing Authority", "Sub-Region", "Demand (MW)", "UTC Time at End of Hour"]


def run() -> pd.DataFrame:
    files = sorted(glob.glob(str(P_EIA / "EIA930_SUBREGION_*.csv.gz"))) or \
            sorted(glob.glob(str(P_EIA / "EIA930_SUBREGION_*.csv")))
    if not files:
        raise FileNotFoundError(f"no EIA-930 files in {P_EIA}")

    parts, rows_in = [], 0
    for f in files:
        d = pd.read_csv(f, usecols=USE, low_memory=False)
        rows_in += len(d)
        d = d[(d["Balancing Authority"] == "PJM") &
              (d["Sub-Region"].isin(EIA_PJM_SUBREGIONS))]
        parts.append(d)
    df = pd.concat(parts, ignore_index=True)

    df["mw"] = pd.to_numeric(df["Demand (MW)"], errors="coerce")
    end = pd.to_datetime(df["UTC Time at End of Hour"], errors="coerce")
    df["datetime_utc"] = end - pd.Timedelta(hours=1)      # hour-ending -> hour-beginning
    df = df.dropna(subset=["datetime_utc", "mw"])
    df = df.drop_duplicates(subset=["datetime_utc", "Sub-Region"], keep="last")

    total = df.groupby("datetime_utc")["mw"].sum().rename("pjm_rto_load_mw")
    count = df.groupby("datetime_utc")["Sub-Region"].nunique()
    dom   = (df[df["Sub-Region"] == "DOM"].set_index("datetime_utc")["mw"]
               .rename("dom_load_mw"))

    out = pd.concat([dom, total], axis=1)
    incomplete = int((count < 18).sum())
    out = out[count.reindex(out.index) >= 18]            # need near-complete PJM coverage
    out = out.sort_index().reset_index()

    out, notes = qa.apply_bounds(out)
    notes.insert(0, "EIA-930 hour-ENDING timestamps shifted back 1h to hour-BEGINNING (UTC)")
    notes.append(f"RTO total = sum of {len(EIA_PJM_SUBREGIONS)} PJM subregions")
    if incomplete:
        notes.append(f"{incomplete:,} hours dropped: fewer than 18 of 20 subregions reporting")
    notes.append("public domain - this is the series safe to publish")
    notes.append(f"span {out.datetime_utc.min():%Y-%m-%d} to {out.datetime_utc.max():%Y-%m-%d}")

    qa.record("load (EIA-930, public)", sources=files, rows_in=rows_in,
              rows_out=len(out), notes=notes)
    qa.write(out, "eia930_load_hourly.csv")
    return out


if __name__ == "__main__":
    run()
