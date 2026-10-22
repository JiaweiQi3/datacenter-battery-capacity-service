"""Join the cleaned hourly sources into one modelling panel.

Canonical key is `datetime_utc`, hour-beginning. UTC is used deliberately:
Eastern Prevailing Time cannot uniquely represent the duplicated hour at the
autumn DST transition, and omits 02:00 in spring. `datetime_ept` is carried
alongside for reading and for anything defined in local terms - PJM's 5CP
window (June-September) and NSPL are both local-clock concepts.
"""
from __future__ import annotations
import pandas as pd
from config import CLEAN, LOAD_SOURCE
import qa

LOAD_FILES = {"pjm": "pjm_load_hourly.csv", "eia": "eia930_load_hourly.csv"}


def run(load_source: str | None = None) -> pd.DataFrame:
    src = (load_source or LOAD_SOURCE).lower()
    if src not in LOAD_FILES:
        raise ValueError(f"load_source must be one of {list(LOAD_FILES)}")

    load_path = CLEAN / LOAD_FILES[src]
    if not load_path.exists():
        alt = "eia" if src == "pjm" else "pjm"
        if (CLEAN / LOAD_FILES[alt]).exists():
            print(f"  {load_path.name} absent - falling back to {LOAD_FILES[alt]}")
            src, load_path = alt, CLEAN / LOAD_FILES[alt]
        else:
            raise FileNotFoundError(f"no cleaned load series in {CLEAN}")

    read = lambda p: pd.read_csv(p, parse_dates=["datetime_utc"])
    master = read(load_path)
    used = [load_path]

    # PJM Data Miner prices may not be redistributed, so the EIA-based
    # (public) panel carries load and weather only.
    joins = ("weather_hourly.csv",) if src == "eia" else ("pjm_lmp_hourly.csv", "weather_hourly.csv")
    for name in joins:
        p = CLEAN / name
        if p.exists():
            master = master.merge(read(p), on="datetime_utc", how="left")
            used.append(p)
        else:
            print(f"  skipping {name} (not present)")

    master = master.sort_values("datetime_utc").reset_index(drop=True)

    # local-clock companion + convenience calendar columns
    ept = (master["datetime_utc"].dt.tz_localize("UTC")
                                 .dt.tz_convert("America/New_York"))
    master.insert(1, "datetime_ept", ept.dt.tz_localize(None))
    master["year"]       = ept.dt.year
    master["month"]      = ept.dt.month
    master["hour_ept"]   = ept.dt.hour
    master["dayofweek"]  = ept.dt.dayofweek          # Monday = 0
    master["is_weekend"] = master["dayofweek"] >= 5

    cov = {c: f"{master[c].notna().mean():.1%}"
           for c in ("dom_load_mw", "pjm_rto_load_mw", "dom_lmp_da", "temp_c")
           if c in master}
    notes = [f"load source: {src.upper()}",
             "key = datetime_utc, hour-beginning; datetime_ept derived for local-clock work",
             f"column coverage: {cov}",
             f"span {master.datetime_utc.min():%Y-%m-%d} to {master.datetime_utc.max():%Y-%m-%d}"]

    qa.record(f"master panel ({src})", sources=used, rows_in=len(master),
              rows_out=len(master), notes=notes)
    name = "dom_hourly_master.csv" if src == "pjm" else "dom_hourly_master_public.csv"
    qa.write(master, name)
    print(f"  -> {CLEAN / name}")
    return master


if __name__ == "__main__":
    import sys
    run(sys.argv[1] if len(sys.argv) > 1 else None)
