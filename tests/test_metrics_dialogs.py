import importlib

import pytest

pytest.importorskip("streamlit")


metrics_dialogs = importlib.import_module("ui.metrics_dialogs")


def test_metric_kind_options_include_strength_session():
    assert "strength_session" in metrics_dialogs._METRIC_KIND_OPTIONS


def test_can_convert_to_strength_session_from_quantitative():
    assert metrics_dialogs._can_convert_kind("quantitative", "strength_session") is True


def test_can_convert_from_strength_session_to_quantitative():
    assert metrics_dialogs._can_convert_kind("strength_session", "quantitative") is True
