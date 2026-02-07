import pytest


pytest.importorskip("streamlit")


from utils import (  # noqa: E402
    format_metric_label,
    normalize_name,
    to_datetz,
)


def test_normalize_name_strips_and_lowercases():
    assert normalize_name("  Sleep  ") == "sleep"


def test_format_metric_label_includes_unit_and_archived():
    metric = {"name": "sleep", "unit_name": "quality", "is_archived": True}
    assert format_metric_label(metric) == "Sleep (Quality) (Archived)"


def test_to_datetz_midday():
    import datetime as dt

    d = dt.date(2026, 2, 7)
    out = to_datetz(d)
    assert out.date() == d
    assert out.time() == dt.time(12, 0)
