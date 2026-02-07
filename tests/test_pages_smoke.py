import pytest


st = pytest.importorskip("streamlit")
AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


def test_tracker_page_renders_overview(monkeypatch):
    import logging
    from ui import pages

    logging.getLogger(
        "streamlit.runtime.scriptrunner_utils.script_run_context"
    ).setLevel(logging.ERROR)

    monkeypatch.setattr(pages.models, "get_metrics", lambda include_archived=True: [{"id": "m1", "name": "x"}])
    monkeypatch.setattr(pages.models, "get_all_entries_bulk", lambda: [])

    def _fake_show_landing_page(all_metrics, all_entries):
        st.write("landing-ok")  # sentinel

    monkeypatch.setattr(pages.landing_page, "show_landing_page", _fake_show_landing_page)

    at = AppTest.from_function(pages.tracker_page)
    at.session_state["tracker_view_selector"] = "Overview"
    at.run()
