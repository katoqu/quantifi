import pytest


pytest.importorskip("streamlit")


import pandas as pd  # noqa: E402

from ui.chart_stats import get_metric_stats  # noqa: E402
from metric_policy import MetricPolicy  # noqa: E402


def test_get_metric_stats_excludes_not_measured_but_keeps_zero():
    """NULL/blank values don’t affect aggregates; numeric 0 remains a valid measurement."""
    df = pd.DataFrame(
        {
            "recorded_at": [
                "2026-02-01T12:00:00Z",
                "2026-02-02T12:00:00Z",
                "2026-02-03T12:00:00Z",
            ],
            "value": [0, None, 2],
        }
    )
    stats = get_metric_stats(df)
    assert stats["count"] == 2
    assert stats["avg"] == pytest.approx(1.0)
    assert stats["latest"] == 2.0
    assert stats["last_date"] == "03 Feb"


def test_get_metric_stats_all_not_measured_returns_no_data():
    """All-NULL/blank series reports “No Data” (not zero)."""
    df = pd.DataFrame(
        {"recorded_at": ["2026-02-01T12:00:00Z", "2026-02-02T12:00:00Z"], "value": [None, ""]}
    )
    stats = get_metric_stats(df)
    assert stats["count"] == 0
    assert stats["avg"] is None
    assert stats["latest"] is None
    assert stats["last_date"] == "No Data"


def test_get_metric_stats_missing_is_zero_affects_avg_and_change():
    df = pd.DataFrame(
        {
            "recorded_at": [
                "2026-02-01T12:00:00Z",
                "2026-02-03T12:00:00Z",
            ],
            "value": [1, 1],
        }
    )
    stats = get_metric_stats(df, policy=MetricPolicy(missing_policy="missing_is_zero", daily_agg="sum"))
    assert stats["count"] == 2
    assert stats["avg"] == pytest.approx(2 / 3)
    assert stats["latest"] == 1.0
    assert stats["change"] == pytest.approx(1.0)
    assert stats["last_date"] == "03 Feb"
