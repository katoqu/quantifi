"""Metric statistics calculation helpers."""

import pandas as pd
from metric_policy import DEFAULT_POLICY, MetricPolicy

from .chart_data import ensure_recorded_at_utc, collapse_to_daily, apply_missing_policy_daily


def get_metric_stats(df, *, policy: MetricPolicy | None = None):
    """Calculate key statistics for a metric: latest, MA7, change, average, count."""
    if df is None or df.empty:
        return {
            "latest": None,
            "ma7": None,
            "change": None,
            "avg": None,
            "count": 0,
            "last_date": "No Data",
        }

    policy = policy or DEFAULT_POLICY
    df = df.copy()
    df = ensure_recorded_at_utc(df)

    df = df.sort_values("recorded_at")

    # Treat NULL/blank as "not measured" (excluded from stats), but keep numeric 0 as valid.
    raw_numeric = pd.to_numeric(df["value"], errors="coerce")
    clean_series = raw_numeric.dropna()
    if clean_series.empty:
        return {
            "latest": None,
            "ma7": None,
            "change": None,
            "avg": None,
            "count": 0,
            "last_date": "No Data",
        }

    last_ts = df[df.index == clean_series.index[-1]]["recorded_at"].iloc[0]

    if policy.missing_policy == "missing_is_zero":
        start_ts = df["recorded_at"].min()
        end_ts = df["recorded_at"].max()
        daily_df = collapse_to_daily(df, policy.daily_agg)
        daily_df = apply_missing_policy_daily(
            daily_df, start_ts=start_ts, end_ts=end_ts, missing_policy=policy.missing_policy
        )
        series = pd.to_numeric(daily_df["value"], errors="coerce").fillna(0.0)

        latest_val = float(series.iloc[-1])
        ma7 = series.rolling(window=7).mean().iloc[-1] if series.shape[0] >= 7 else None
        change = float(series.iloc[-1] - series.iloc[-2]) if series.shape[0] >= 2 else 0.0
        avg_val = float(series.mean())
    else:
        latest_val = float(clean_series.iloc[-1])
        ma7 = clean_series.rolling(window=7).mean().iloc[-1] if len(clean_series) >= 7 else None
        change = float(clean_series.iloc[-1] - clean_series.iloc[-2]) if len(clean_series) >= 2 else 0.0
        avg_val = float(clean_series.mean())

    return {
        "latest": latest_val,
        "ma7": ma7,
        "change": change,
        "avg": avg_val,
        "count": int(clean_series.shape[0]),
        "last_date": last_ts.strftime("%d %b"),
    }
