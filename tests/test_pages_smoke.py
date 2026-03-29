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
    at.session_state["tracker_view_selector"] = "Home"
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
    at.session_state["tracker_view_selector"] = "Home"
    at.run()

    assert len(at.exception) == 0
    assert any(el.value == "landing-empty-ok" for el in at.text)


def test_tracker_page_renders_changes(monkeypatch):
    """Tracker page can route to the Changes view without selecting a metric."""
    import logging

    logging.getLogger(
        "streamlit.runtime.scriptrunner_utils.script_run_context"
    ).setLevel(logging.ERROR)

    script = """
import streamlit as st
from ui import pages

pages.models.get_metrics = lambda include_archived=True: [{"id": "m1", "name": "x"}]

def _fake_show_changes():
    st.text("changes-ok")  # sentinel

pages.changes.show_changes = _fake_show_changes

pages.tracker_page()
"""

    at = AppTest.from_string(script)
    at.session_state["tracker_view_selector"] = "Log"
    at.run()

    assert len(at.exception) == 0
    assert any(el.value == "changes-ok" for el in at.text)


def test_tracker_page_add_renders_filtered_dropdown(monkeypatch):
    """Add view renders pills filter and dropdown metric selector."""
    import logging

    logging.getLogger(
        "streamlit.runtime.scriptrunner_utils.script_run_context"
    ).setLevel(logging.ERROR)

    script = """
import streamlit as st
from ui import pages

pages.models.get_metrics = lambda include_archived=True: [
    {"id": "m1", "name": "sleep", "unit_name": "hrs"},
    {"id": "m2", "name": "mood", "unit_name": "score"},
]

pages.models.get_all_entries_bulk = lambda: [
    {"metric_id": "m2", "recorded_at": "2024-01-01T00:00:00Z", "value": 5}
]

pages.tracker_page()
"""

    at = AppTest.from_string(script)
    at.session_state["tracker_view_selector"] = "Add"
    at.session_state["tracker_subview_cat_filter"] = "Recent"
    at.run()

    assert len(at.exception) == 0
    assert len(at.selectbox) == 1
