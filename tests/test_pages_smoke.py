import pytest


st = pytest.importorskip("streamlit")
AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


def test_tracker_page_renders_overview(monkeypatch):
    """Tracker page renders and calls the landing view (happy path)."""
    import logging

    logging.getLogger(
        "streamlit.runtime.scriptrunner_utils.script_run_context"
    ).setLevel(logging.ERROR)

    script = """
import streamlit as st
from ui import pages

pages.models.get_metrics = lambda include_archived=True: [{"id": "m1", "name": "x"}]
pages.models.get_all_entries_bulk = lambda: []

def _fake_show_landing_page(all_metrics, all_entries):
    st.text("landing-ok")  # sentinel

pages.landing_page.show_landing_page = _fake_show_landing_page

pages.tracker_page()
"""

    at = AppTest.from_string(script)
    at.session_state["tracker_view_selector"] = "Overview"
    at.run()

    assert len(at.exception) == 0
    assert any(el.value == "landing-ok" for el in at.text)


def test_tracker_page_renders_overview_with_no_metrics(monkeypatch):
    """Regression: new users with no metrics still see a landing-state screen."""
    import logging

    logging.getLogger(
        "streamlit.runtime.scriptrunner_utils.script_run_context"
    ).setLevel(logging.ERROR)

    script = """
import streamlit as st
from ui import pages

pages.models.get_metrics = lambda include_archived=True: []
pages.models.get_all_entries_bulk = lambda: []

def _fake_show_landing_page(all_metrics, all_entries):
    assert all_metrics == []
    st.text("landing-empty-ok")  # sentinel

pages.landing_page.show_landing_page = _fake_show_landing_page

pages.tracker_page()
"""

    at = AppTest.from_string(script)
    at.session_state["tracker_view_selector"] = "Overview"
    at.run()

    assert len(at.exception) == 0
    assert any(el.value == "landing-empty-ok" for el in at.text)
