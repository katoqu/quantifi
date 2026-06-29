import importlib

import pandas as pd
import pytest

pytest.importorskip("streamlit")


capture = importlib.import_module("ui.capture")


def test_is_strength_metric_detects_strength_session_kind():
    assert capture._is_strength_metric({"metric_kind": "strength_session"}) is True


def test_is_strength_metric_returns_false_for_standard_metrics():
    assert capture._is_strength_metric({"metric_kind": "quantitative"}) is False
    assert capture._is_strength_metric({}) is False


def test_format_success_value_uses_strength_summary_when_present():
    payload = {"summary": "80.0 kg × 5 reps × 3 sets"}
    assert capture._format_success_value(payload, None, "kg") == "80.0 kg × 5 reps × 3 sets"


def test_format_success_value_falls_back_to_numeric_value():
    assert capture._format_success_value(None, 72.5, "kg") == "72.5 kg"


def test_render_strength_workout_form_builds_multiple_sets(monkeypatch):
    import streamlit as st

    captured = {}

    def fake_data_editor(df, **kwargs):
        captured["df"] = df.copy()
        return pd.DataFrame([{"load_kg": 80.0, "reps": 5}, {"load_kg": 82.5, "reps": 3}])

    monkeypatch.setattr(st, "data_editor", fake_data_editor)
    monkeypatch.setattr(capture.st, "session_state", {})

    result = capture._render_strength_workout_form("test", "kg")

    assert result["summary"] == "80.0 kg × 5/3 reps × 2 sets"
    assert result["sets"][1]["load_kg"] == 82.5
