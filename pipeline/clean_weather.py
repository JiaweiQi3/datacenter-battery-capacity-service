"""Hourly weather at Dulles (IAD) from two archives.

NOAA ISD is the canonical archive but lags - at time of writing it stops at
2025-08-27, which would leave the entire 2026 peak season without temperature.
The Iowa Environmental Mesonet ASOS archive carries the same METAR observations
and is current, so it fills forward. Where both cover an hour, ISD wins.

ISD packs value and quality into one field: "+0072,5" is +7.2 C, quality 5.
Temperature and dew point are tenths of a degree Celsius, sea-level pressure
tenths of a hectopascal, missing is +9999 / 99999. Only FM-15 (METAR) reports
are kept - one observation per hour at :52, the standard hourly observation.

IEM reports degrees Fahrenheit and is converted here.
"""
from __future__ import annotations
import glob
import pandas as pd
from config import P_WEATHER, WEATHER_REPORT_TYPE, ISD_MISSING
import qa

ISD_USE = ["DATE", "REPORT_TYPE", "TMP", "DEW", "SLP"]
COLS = ["temp_c", "dewpoint_c", "slp_hpa"]


def _scaled(series: pd.Series, divisor: float) -> pd.Series:
    val = series.astype("string").str.split(",", n=1).str[0].str.strip()
    val = val.where(~val.isin(ISD_MISSING))
    return pd.to_numeric(val, errors="coerce") / divisor


def _read_isd(files) -> tuple[pd.DataFrame, int]:
    parts, rows_in = [], 0
    for f in files:
        d = pd.read_csv(f, usecols=lambda c: c in ISD_USE, low_memory=False)
        rows_in += len(d)
        parts.append(d[d["REPORT_TYPE"].str.strip() == WEATHER_REPORT_TYPE])
    if not parts:
        return pd.DataFrame(columns=["datetime_utc", *COLS]), 0
    df = pd.concat(parts, ignore_index=True)
    out = pd.DataFrame({
        "datetime_utc": pd.to_datetime(df["DATE"], errors="coerce").dt.floor("h"),
        "temp_c":     _scaled(df["TMP"], 10),
        "dewpoint_c": _scaled(df["DEW"], 10),
        "slp_hpa":    _scaled(df["SLP"], 10),
    })
    return out.dropna(subset=["datetime_utc"]), rows_in


def _read_iem(files) -> tuple[pd.DataFrame, int]:
    parts, rows_in = [], 0
    for f in files:
        d = pd.read_csv(f, na_values=["M", "T", ""], low_memory=False)
        rows_in += len(d); parts.append(d)
    if not parts:
        return pd.DataFrame(columns=["datetime_utc", *COLS]), 0
    df = pd.concat(parts, ignore_index=True)
    f2c = lambda s: (pd.to_numeric(s, errors="coerce") - 32) * 5 / 9
    out = pd.DataFrame({
        "datetime_utc": pd.to_datetime(df["valid"], errors="coerce").dt.floor("h"),
        "temp_c":     f2c(df.get("tmpf")),
        "dewpoint_c": f2c(df.get("dwpf")),
        "slp_hpa":    pd.to_numeric(df.get("mslp"), errors="coerce"),
    })
    return out.dropna(subset=["datetime_utc"]), rows_in


def run() -> pd.DataFrame:
    isd_files = sorted(glob.glob(str(P_WEATHER / "iad_*.csv")))
    iem_files = sorted(glob.glob(str(P_WEATHER / "iem_iad_*.csv")))
    if not (isd_files or iem_files):
        raise FileNotFoundError(f"no weather files in {P_WEATHER}")

    isd, n_isd = _read_isd(isd_files)
    iem, n_iem = _read_iem(iem_files)

    notes = [f"kept REPORT_TYPE == {WEATHER_REPORT_TYPE} (METAR) only",
             "ISD: tenths of degrees C / hPa; +9999, 99999 -> NaN. IEM: degrees F converted to C"]

    # agreement check on the overlap - a free validation of the splice
    if len(isd) and len(iem):
        ov = isd.merge(iem, on="datetime_utc", suffixes=("_isd", "_iem"))
        if len(ov):
            diff = (ov["temp_c_isd"] - ov["temp_c_iem"]).abs()
            notes.append(f"ISD/IEM overlap {len(ov):,} hours; mean |temp difference| "
                         f"{diff.mean():.2f} C, max {diff.max():.2f} C (ISD kept)")

    # IEM first, ISD second, keep='last' so ISD wins any shared hour
    df = pd.concat([iem, isd], ignore_index=True)
    before = len(df)
    df = (df.sort_values("datetime_utc")
            .drop_duplicates(subset=["datetime_utc"], keep="last"))
    collapsed = before - len(df)

    out = df.groupby("datetime_utc", as_index=False)[COLS].mean().sort_values("datetime_utc")
    out, bnotes = qa.apply_bounds(out)
    notes += bnotes
    if collapsed:
        notes.append(f"{collapsed:,} duplicate hours collapsed (ISD preferred over IEM)")
    if n_iem:
        notes.append(f"IEM ASOS fills forward from NOAA ISD's archive lag ({len(iem):,} obs)")
    miss = int(out["temp_c"].isna().sum())
    if miss:
        notes.append(f"{miss:,} hours have no valid temperature")
    notes.append(f"span {out.datetime_utc.min():%Y-%m-%d} to {out.datetime_utc.max():%Y-%m-%d}")

    qa.record("weather (METAR, ISD+IEM)", sources=isd_files + iem_files,
              rows_in=n_isd + n_iem, rows_out=len(out), notes=notes)
    qa.write(out, "weather_hourly.csv")
    return out


if __name__ == "__main__":
    run()
