"""PJM day-ahead hourly LMPs -> DOM and PJM-RTO zonal prices."""
from __future__ import annotations
import glob
import pandas as pd
from config import P_LMP, LMP_NODES, PJM_DT_FMT
import qa

USE = ["datetime_beginning_utc", "pnode_name", "system_energy_price_da",
       "total_lmp_da", "congestion_price_da", "marginal_loss_price_da",
       "row_is_current", "version_nbr"]


def run() -> pd.DataFrame:
    files = sorted(glob.glob(str(P_LMP / "*.csv")))
    if not files:
        raise FileNotFoundError(f"no CSVs in {P_LMP}")

    parts, rows_in = [], 0
    for f in files:
        d = pd.read_csv(f, usecols=USE, low_memory=False)
        rows_in += len(d)
        parts.append(d[d["pnode_name"].isin(LMP_NODES)])
    df = pd.concat(parts, ignore_index=True)

    df["datetime_utc"] = pd.to_datetime(df["datetime_beginning_utc"], format=PJM_DT_FMT)
    df["version_nbr"] = pd.to_numeric(df["version_nbr"], errors="coerce").fillna(0)

    # PJM restates prices; keep the current/highest version per node-hour
    before = len(df)
    df = (df.sort_values(["datetime_utc", "pnode_name", "row_is_current", "version_nbr"])
            .drop_duplicates(subset=["datetime_utc", "pnode_name"], keep="last"))
    superseded = before - len(df)

    dom = (df[df.pnode_name == "DOM"]
           .set_index("datetime_utc")[["total_lmp_da", "system_energy_price_da",
                                       "congestion_price_da", "marginal_loss_price_da"]]
           .rename(columns={"total_lmp_da": "dom_lmp_da",
                            "system_energy_price_da": "dom_energy_da",
                            "congestion_price_da": "dom_congestion_da",
                            "marginal_loss_price_da": "dom_loss_da"}))
    rto = (df[df.pnode_name == "PJM-RTO"]
           .set_index("datetime_utc")[["total_lmp_da"]]
           .rename(columns={"total_lmp_da": "pjm_rto_lmp_da"}))

    out = dom.join(rto, how="outer").sort_index().reset_index()

    notes = [f"kept nodes {sorted(LMP_NODES)}",
             f"span {out.datetime_utc.min():%Y-%m-%d} to {out.datetime_utc.max():%Y-%m-%d}"]
    if superseded:
        notes.append(f"{superseded:,} superseded price versions dropped (kept row_is_current / max version_nbr)")
    notes.append("DST spring-forward hours are absent by construction; year-boundary gaps reflect "
                 "export end dates of 12/31 00:00")

    qa.record("day-ahead LMP", sources=files, rows_in=rows_in, rows_out=len(out), notes=notes)
    qa.write(out, "pjm_lmp_hourly.csv")
    return out


if __name__ == "__main__":
    run()
