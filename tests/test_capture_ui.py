import pytest


st = pytest.importorskip("streamlit")
AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


def test_add_tab_chart_toggle_controls_visualization_render():
    """Add tab: chart toggle defaults off and enables visualization when turned on."""
    script = """
import streamlit as st
from ui import capture

# Avoid widget-state edge cases in Streamlit testing for pills.
capture.st.pills = lambda *a, **k: "Now"

metric = {
    "id": "m1",
    "name": "sleep",
    "unit_name": "quality",
    "metric_kind": "quantitative",
    "unit_type": "float",
}

capture.models.get_latest_entry_only = lambda _mid: {"value": 1.0}
capture.models.get_recent_numeric_values = lambda _mid, limit=5: [1.0, 2.0]
capture.models.get_entries = lambda _mid=None: []
import pandas as pd
capture.utils.collect_data = lambda _m: (pd.DataFrame([{"recorded_at": "2026-02-01T12:00:00Z", "value": 1.0}]), "quality", "Sleep")

def _viz(*args, **kwargs):
    st.text("viz-called")

capture.visualize.show_visualizations = _viz

capture.show_tracker_suite(metric)
"""

    at = AppTest.from_string(script)
    at.run()

    # Default: chart toggle off => visualization not rendered.
    assert not any(el.value == "viz-called" for el in at.text)

    # Toggle on and rerun.
    assert len(at.toggle) == 1
    at.toggle[0].set_value(True)
    at.run()

    assert any(el.value == "viz-called" for el in at.text)
