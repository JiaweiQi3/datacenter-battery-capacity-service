"""Shared helpers: provenance recording and plausibility filtering.

Every cleaner records what it read, what it dropped and why. That log is the
methodology section of the report - it is not incidental output.
"""
from __future__ import annotations
import json, datetime as dt
from pathlib import Path
import pandas as pd
from config import CLEAN, BOUNDS

_LOG: list[dict] = []


def record(step: str, *, sources, rows_in: int, rows_out: int, notes=None):
    entry = {
        "step": step,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "sources": [str(s) for s in (sources if isinstance(sources, (list, tuple)) else [sources])],
        "rows_in": int(rows_in),
        "rows_out": int(rows_out),
        "rows_dropped": int(rows_in - rows_out),
        "notes": notes or [],
    }
    _LOG.append(entry)
    drop = f"  (-{entry['rows_dropped']:,})" if entry["rows_dropped"] else ""
    print(f"  {step:<22} {rows_out:>9,} rows{drop}")
    for n in entry["notes"]:
        print(f"      note: {n}")
    return entry


def apply_bounds(df: pd.DataFrame, cols=None) -> tuple[pd.DataFrame, list[str]]:
    """Null out implausible values. Returns (df, notes). Never silently corrects."""
    notes = []
    for col in (cols or df.columns):
        if col not in BOUNDS or col not in df.columns:
            continue
        lo, hi = BOUNDS[col]
        bad = df[col].notna() & (~df[col].between(lo, hi))
        if bad.any():
            examples = df.loc[bad, col].head(3).round(0).tolist()
            notes.append(
                f"{col}: {int(bad.sum())} value(s) outside [{lo:,}, {hi:,}] set to NaN; e.g. {examples}"
            )
            df.loc[bad, col] = pd.NA
    return df, notes


def write(df: pd.DataFrame, name: str) -> Path:
    path = CLEAN / name
    df.to_csv(path, index=False)
    return path


def write_report(path: Path | None = None) -> Path:
    path = path or (CLEAN / "data_quality_report.md")
    lines = [
        "# Data quality and provenance report",
        "",
        f"Generated {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC by `pipeline/run_all.py`.",
        "",
        "Every cleaned file below is reproducible from the raw downloads in `original_data/`.",
        "Rows dropped or set to missing are counted per step with the reason; nothing is silently corrected.",
        "",
    ]
    for e in _LOG:
        lines += [f"## {e['step']}", "",
                  f"- rows in: **{e['rows_in']:,}** → out: **{e['rows_out']:,}** "
                  f"(dropped {e['rows_dropped']:,})"]
        if e["sources"]:
            src = ", ".join(Path(s).name for s in e["sources"][:6])
            more = f" (+{len(e['sources'])-6} more)" if len(e["sources"]) > 6 else ""
            lines.append(f"- sources: {src}{more}")
        for n in e["notes"]:
            lines.append(f"- {n}")
        lines.append("")
    path.write_text("\n".join(lines))
    (CLEAN / "provenance.json").write_text(json.dumps(_LOG, indent=2))
    return path
