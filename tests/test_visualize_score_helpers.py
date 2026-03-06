import pytest


pytest.importorskip("streamlit")


from ui.visualize import _score_resample_agg, _score_yaxis_range  # noqa: E402


def test_score_resample_agg_uses_mean_when_missing_is_zero():
    assert _score_resample_agg(missing_policy="missing_is_zero") == "mean"
    assert _score_resample_agg(missing_policy="ignore_missing") == "median"


def test_score_yaxis_range_includes_zero_when_missing_is_zero():
    y0, y1 = _score_yaxis_range(range_start=1, range_end=5, missing_policy="missing_is_zero")
    assert y0 <= 0
    assert y1 >= 5
