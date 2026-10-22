"""Smaller sources: ancillary reserves, regulation, NSPL, load forecasts."""
from __future__ import annotations
import glob, re
import pandas as pd
from config import (P_ANCILLARY, P_NSPL, P_REG, P_FORECAST, PJM_DT_FMT)
import qa

_slug = lambda s: re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


def ancillary() -> pd.DataFrame:
    """Day-ahead ancillary service LMPs -> one column per reserve product."""
    files = sorted(glob.glob(str(P_ANCILLARY / "*.csv")))
    if not files:
        raise FileNotFoundError(f"no CSVs in {P_ANCILLARY}")
    parts, rows_in = [], 0
    for f in files:
        d = pd.read_csv(f, low_memory=False)
        rows_in += len(d); parts.append(d)
    df = pd.concat(parts, ignore_index=True)

    df["datetime_utc"] = pd.to_datetime(df["datetime_beginning_utc"], format=PJM_DT_FMT)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    if "version_nbr" in df:
        df["version_nbr"] = pd.to_numeric(df["version_nbr"], errors="coerce").fillna(0)
        df = df.sort_values(["datetime_utc", "ancillary_service", "version_nbr"])
    before = len(df)
    df = df.drop_duplicates(subset=["datetime_utc", "ancillary_service"], keep="last")

    out = (df.pivot(index="datetime_utc", columns="ancillary_service", values="value")
             .rename(columns=_slug).sort_index().reset_index())
    out.columns.name = None

    notes = ["one column per reserve product; Mid-Atlantic/Dominion series are the relevant ones",
             "PJM's October 2025 ancillary redesign means pre/post periods are not comparable",
             f"span {out.datetime_utc.min():%Y-%m-%d} to {out.datetime_utc.max():%Y-%m-%d}"]
    if before - len(df):
        notes.append(f"{before-len(df):,} superseded versions dropped")
    qa.record("ancillary reserves", sources=files, rows_in=rows_in, rows_out=len(out), notes=notes)
    qa.write(out, "ancillary_reserve_hourly.csv")
    return out


def regulation() -> pd.DataFrame:
    df = pd.read_csv(P_REG, low_memory=False); rows_in = len(df)
    df["datetime_utc"] = pd.to_datetime(df["datetime_beginning_utc"], format=PJM_DT_FMT)
    for c in ("market_clearing_price", "market_capped_clearing_price",
              "capability_clearing_price", "performance_clearing_price"):
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    out = (df.drop(columns=[c for c in ("datetime_beginning_utc", "datetime_beginning_ept") if c in df])
             .drop_duplicates(subset=["datetime_utc", "area"] if "area" in df else ["datetime_utc"])
             .sort_values("datetime_utc"))
    cols = ["datetime_utc"] + [c for c in out.columns if c != "datetime_utc"]
    out = out[cols]
    qa.record("regulation prices", sources=P_REG, rows_in=rows_in, rows_out=len(out),
              notes=["5-minute resolution; feed retains only a short rolling window",
                     "post-Oct-2025 design splits pay into capability + performance",
                     f"span {out.datetime_utc.min():%Y-%m-%d} to {out.datetime_utc.max():%Y-%m-%d}"])
    qa.write(out, "regulation_5min.csv")
    return out


def nspl() -> pd.DataFrame:
    """Annual zonal Network Service Peak Loads - the transmission charge basis."""
    files = sorted(glob.glob(str(P_NSPL / "*.csv")))
    if not files:
        raise FileNotFoundError(f"no CSVs in {P_NSPL}")
    parts, rows_in = [], 0
    for f in files:
        d = pd.read_csv(f, low_memory=False); rows_in += len(d); parts.append(d)
    df = pd.concat(parts, ignore_index=True).drop_duplicates(subset=["year", "zone"])
    out = df[df["zone"] == "DOM"].copy()
    out["peak_datetime_utc"] = pd.to_datetime(out["datetime_beginning_utc"], format=PJM_DT_FMT)
    out["peak_datetime_ept"] = pd.to_datetime(out["datetime_beginning_ept"], format=PJM_DT_FMT)
    out = (out[["year", "zone", "peak_datetime_utc", "peak_datetime_ept", "nspl_mw"]]
             .sort_values("year").reset_index(drop=True))
    qa.record("NSPL (DOM)", sources=files, rows_in=rows_in, rows_out=len(out),
              notes=["NSPL = zone's highest hour Nov 1 -> Oct 31, setting transmission charges",
                     "distinct from the capacity 5CP, which uses PJM SYSTEM peaks in Jun-Sep",
                     f"effective years {out.year.min()}-{out.year.max()}"])
    qa.write(out, "nspl_dom_annual.csv")
    return out


def forecast() -> pd.DataFrame:
    """PJM historical day-ahead load forecasts, DOM area."""
    df = pd.read_csv(P_FORECAST, low_memory=False); rows_in = len(df)
    areas = set(df["forecast_area"].unique())
    keep = {a for a in areas if a.upper() in {"DOM", "RTO", "PJM RTO", "PJM-RTO"}}
    out = df[df["forecast_area"].isin(keep)].copy()
    out["evaluated_at_utc"] = pd.to_datetime(out["evaluated_at_utc"], format=PJM_DT_FMT)
    out["forecast_hour_utc"] = pd.to_datetime(out["forecast_hour_beginning_utc"], format=PJM_DT_FMT)
    out["lead_hours"] = (out["forecast_hour_utc"] - out["evaluated_at_utc"]).dt.total_seconds() / 3600
    out = (out[["evaluated_at_utc", "forecast_hour_utc", "lead_hours",
                "forecast_area", "forecast_load_mw"]]
             .sort_values(["forecast_hour_utc", "evaluated_at_utc"]))
    qa.record("load forecasts", sources=P_FORECAST, rows_in=rows_in, rows_out=len(out),
              notes=[f"kept forecast_area in {sorted(keep)} (of {len(areas)} areas)",
                     "lead_hours = forecast horizon; the key Mini 2 feature and industry baseline"])
    qa.write(out, "load_forecast_hist.csv")
    return out


def run():
    ancillary(); regulation(); nspl(); forecast()


if __name__ == "__main__":
    run()
