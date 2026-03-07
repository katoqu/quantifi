import pytest


pytest.importorskip("streamlit")


import pandas as pd  # noqa: E402

from ui.chart_data import resolve_period, resample_to_plot_df  # noqa: E402


def test_resolve_period_all_long_span_uses_month_start():
    spec = resolve_period(
        "All",
        min_ts=pd.Timestamp("2025-01-01T00:00:00Z"),
        max_ts=pd.Timestamp("2026-03-01T00:00:00Z"),
        anchor_end_ts=pd.Timestamp("2026-03-07T23:59:59Z"),
    )
    assert spec.freq == "MS"
    assert spec.tickformat == "%b '%y"
    assert spec.hover_date_fmt == "%b %Y"
    assert spec.start_ts == pd.Timestamp("2025-01-01T00:00:00Z")


def test_resolve_period_week_is_trailing_to_anchor_end():
    anchor_end = pd.Timestamp("2026-03-07T23:59:59Z")
    spec = resolve_period(
        "Week",
        min_ts=pd.Timestamp("2026-01-01T00:00:00Z"),
        max_ts=pd.Timestamp("2026-03-01T00:00:00Z"),
        anchor_end_ts=anchor_end,
    )
    assert spec.end_ts == anchor_end
    assert spec.start_ts == anchor_end - pd.Timedelta(days=7)
    assert spec.freq == "D"


def test_resample_to_plot_df_count_sum_min_count_drops_all_nan():
    daily_df = pd.DataFrame(
        {
            "recorded_at": ["2026-03-01T12:00:00Z", "2026-03-02T12:00:00Z"],
            "value": [None, None],
        }
    )
    plot_df, agg = resample_to_plot_df(daily_df, freq="W", kind="count", missing_policy="ignore_missing")
    assert agg == "sum"
    assert plot_df.empty


def test_resample_to_plot_df_score_missing_is_zero_uses_mean():
    # Simulate "missing is zero" by including explicit zeros in the daily series.
    daily_df = pd.DataFrame(
        {
            # Use Mon-Wed so all points fall into the same default pandas "W" bucket (week ending Sunday).
            "recorded_at": ["2026-03-02T12:00:00Z", "2026-03-03T12:00:00Z", "2026-03-04T12:00:00Z"],
            "value": [0, 0, 4],
        }
    )
    plot_df, agg = resample_to_plot_df(daily_df, freq="W", kind="score", missing_policy="missing_is_zero")
    assert agg == "mean"
    assert plot_df.shape[0] == 1
    assert plot_df["value"].iloc[0] == pytest.approx(4 / 3)
