import pytest


pytest.importorskip("streamlit")


from utils import (  # noqa: E402
    format_entry_summary,
    format_metric_label,
    normalize_name,
    to_datetz,
)


def test_normalize_name_strips_and_lowercases():
    """Name normalization is stable (trim + lowercase)."""
    assert normalize_name("  Sleep  ") == "sleep"


def test_format_metric_label_includes_unit_and_archived():
    """Label includes unit name and archived marker."""
    metric = {"name": "sleep", "unit_name": "quality", "is_archived": True}
    assert format_metric_label(metric) == "Sleep (Quality) (Archived)"


def test_to_datetz_midday():
    """Date converts to tz-aware midday datetime."""
    import datetime as dt

    d = dt.date(2026, 2, 7)
    out = to_datetz(d)
    assert out.date() == d
    assert out.time() == dt.time(12, 0)


def test_format_entry_summary_uses_structured_sets_when_present():
    """Structured workout sets render a human-readable summary."""
    entry = {
        "value": 80.0,
        "load_kg": 80.0,
        "sets": [{"load_kg": 80.0, "reps": 10}, {"load_kg": 75.0, "reps": 8}],
    }
    assert format_entry_summary(entry) == "80.0 kg × 10/8 reps"


def test_format_entry_summary_falls_back_to_plain_value():
    """Simple entries still show their numeric value when no details exist."""
    entry = {"value": 72.5}
    assert format_entry_summary(entry) == "72.5"
