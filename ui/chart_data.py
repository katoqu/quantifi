"""Data transformation and resampling helpers for metric charts."""

import pandas as pd
from dataclasses import dataclass


@dataclass(frozen=True)
class _PeriodSpec:
    start_ts: pd.Timestamp
    end_ts: pd.Timestamp
    freq: str
    tickformat: str
    hover_label: str
    hover_date_fmt: str


def ensure_recorded_at_utc(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure recorded_at column is in UTC timezone."""
    if df is None or df.empty:
        return df
    if not pd.api.types.is_datetime64_any_dtype(df["recorded_at"]):
        df["recorded_at"] = pd.to_datetime(df["recorded_at"], format="mixed", utc=True)
    elif df["recorded_at"].dt.tz is None:
        df["recorded_at"] = df["recorded_at"].dt.tz_localize("UTC")
    return df


def resolve_period(
    range_choice: str,
    *,
    min_ts: pd.Timestamp,
    max_ts: pd.Timestamp,
    anchor_end_ts: pd.Timestamp,
) -> _PeriodSpec:
    """
    Map a period selection to filtering bounds + resample config.

    `anchor_end_ts` decides whether "Week/Month/6M/Year" is trailing-to-today or trailing-to-last-point.
    """
    choice = (range_choice or "").strip()
    if choice in {"6m", "6 M"}:
        choice = "6M"

    # Default hover date format (includes day)
    hover_date_fmt = "%d %b %Y"

    end_ts = anchor_end_ts

    if choice == "Week":
        start_ts = end_ts - pd.Timedelta(days=7)
        freq, tickformat, hover_label = "D", "%a", "Value"
    elif choice == "Month":
        start_ts = end_ts - pd.Timedelta(days=31)
        freq, tickformat, hover_label = "D", "%d", "Daily Value"
    elif choice == "6M":
        start_ts = end_ts - pd.DateOffset(months=6)
        freq, tickformat, hover_label = "W", "%d %b", "Weekly Avg"
    elif choice == "Year":
        start_ts = end_ts - pd.DateOffset(months=12)
        freq, tickformat, hover_label = "W", "%b", "Weekly Avg"
    else:
        # "All" or "Custom"
        start_ts = min_ts
        days_diff = (max_ts - min_ts).days if pd.notna(max_ts) and pd.notna(min_ts) else 0
        if days_diff <= 31:
            freq, tickformat, hover_label = "D", "%d %b", "Daily Value"
        elif days_diff <= 150:
            freq, tickformat, hover_label = "W", "%d %b", "Weekly Avg"
        else:
            freq, tickformat, hover_label = "MS", "%b '%y", "Monthly Avg"
            hover_date_fmt = "%b %Y"

    return _PeriodSpec(
        start_ts=pd.Timestamp(start_ts).tz_convert("UTC") if pd.Timestamp(start_ts).tzinfo else pd.Timestamp(start_ts, tz="UTC"),
        end_ts=pd.Timestamp(end_ts).tz_convert("UTC") if pd.Timestamp(end_ts).tzinfo else pd.Timestamp(end_ts, tz="UTC"),
        freq=freq,
        tickformat=tickformat,
        hover_label=hover_label,
        hover_date_fmt=hover_date_fmt,
    )


def resample_to_plot_df(
    daily_df: pd.DataFrame,
    *,
    freq: str,
    kind: str,
    missing_policy: str,
) -> tuple[pd.DataFrame, str]:
    """
    Resample daily values into the plot series.
    Returns (plot_df, agg_kind) where agg_kind is one of {"mean","median","sum"}.
    """
    if daily_df is None or daily_df.empty:
        return pd.DataFrame(columns=["recorded_at", "value"]), "mean"

    df = daily_df.copy()
    df["recorded_at"] = pd.to_datetime(df["recorded_at"], utc=True, format="mixed")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    if kind == "score":
        agg_kind = score_resample_agg(missing_policy=missing_policy)
    elif kind == "count":
        agg_kind = "mean"
    else:
        agg_kind = "mean"

    g = df.set_index("recorded_at")["value"].resample(freq)
    if agg_kind == "sum":
        s = g.sum(min_count=1)
    elif agg_kind == "median":
        s = g.median()
    else:
        s = g.mean()

    plot_df = (
        s.dropna()
        .rename("value")
        .rename_axis("recorded_at")
        .reset_index()
    )
    return plot_df[["recorded_at", "value"]], agg_kind


def collapse_to_daily(df: pd.DataFrame, daily_agg: str) -> pd.DataFrame:
    """Collapse raw data to daily aggregates."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["recorded_at", "value"])

    df = df.sort_values("recorded_at").copy()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["_day"] = df["recorded_at"].dt.floor("D")

    if daily_agg == "mean":
        agg_func = "mean"
    elif daily_agg == "last":
        agg_func = lambda s: s.dropna().iloc[-1] if s.dropna().shape[0] else float("nan")
    elif daily_agg == "max":
        agg_func = "max"
    elif daily_agg == "min":
        agg_func = "min"
    else:
        agg_func = lambda s: s.sum(min_count=1)

    daily_grouped = df.groupby("_day", as_index=True)["value"].agg(agg_func)
    daily = daily_grouped.reset_index().rename(columns={"_day": "recorded_at"})
    return daily[["recorded_at", "value"]]


def apply_missing_policy_daily(
    daily_df: pd.DataFrame, *, start_ts: pd.Timestamp, end_ts: pd.Timestamp, missing_policy: str
) -> pd.DataFrame:
    """Apply missing data policy (fill zero or leave gaps)."""
    if missing_policy != "missing_is_zero":
        return daily_df

    start_day = start_ts.floor("D")
    end_day = end_ts.floor("D")
    if pd.isna(start_day) or pd.isna(end_day) or start_day > end_day:
        return daily_df

    all_days = pd.date_range(start=start_day, end=end_day, freq="D", tz="UTC")
    filled = (
        daily_df.set_index("recorded_at")["value"]
        .reindex(all_days)
        .fillna(0.0)
        .rename_axis("recorded_at")
        .reset_index()
    )
    return filled[["recorded_at", "value"]]


def score_resample_agg(*, missing_policy: str) -> str:
    """Get aggregation method for score kind."""
    return "median"


def score_yaxis_range(*, range_start: int, range_end: int, missing_policy: str) -> tuple[float, float]:
    """Calculate Y-axis range for score kind."""
    if missing_policy == "missing_is_zero":
        range_start = min(int(range_start), 0)
    return (float(range_start) - 0.5, float(range_end) + 0.5)
