"""Streamlit UI tests for the Lifestyle Changes feature."""

import pytest


st = pytest.importorskip("streamlit")
AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


def test_changes_can_create_event():
    """Creating a change event calls the model with category + title + notes."""
    script = """
import streamlit as st
from ui import changes

EVENTS_KEY = "__events"
CATS_KEY = "__cats"
CALLS_KEY = "__create_calls"

if EVENTS_KEY not in st.session_state:
    st.session_state[EVENTS_KEY] = []
if CATS_KEY not in st.session_state:
    st.session_state[CATS_KEY] = [{"id": "c1", "name": "fitness"}]
if CALLS_KEY not in st.session_state:
    st.session_state[CALLS_KEY] = []

def _get_categories():
    return st.session_state[CATS_KEY]

def _get_change_events(limit=200):
    return st.session_state[EVENTS_KEY]

def _create_change_event(payload):
    st.session_state[CALLS_KEY].append(payload)
    st.session_state[EVENTS_KEY] = [
        {
            "id": "e1",
            "title": payload.get("title"),
            "notes": payload.get("notes"),
            "recorded_at": payload.get("recorded_at"),
            "category_id": payload.get("category_id"),
            "categories": {"name": "fitness"},
        }
    ]
    return {"data": [{"id": "e1"}]}

changes.models.get_categories = _get_categories
changes.models.get_change_events = _get_change_events
changes.models.create_change_event = _create_change_event
changes.models.delete_change_event = lambda _id: None
changes.models.update_change_event = lambda _id, payload: None

changes.show_changes()
"""

    at = AppTest.from_string(script)
    at.run()

    at.text_input[0].input("Started vegetarian nutrition")
    at.text_area[0].input("No meat, fish ok.")
    at.form_submit_button[0].click()
    at.run()

    calls = at.session_state.get("__create_calls", [])
    assert len(calls) == 1
    assert calls[0]["title"] == "Started vegetarian nutrition"
    assert calls[0]["notes"] == "No meat, fish ok."
    assert calls[0]["category_id"] == "c1"
    assert "recorded_at" in calls[0]


def test_changes_can_edit_event():
    """Editing a change event calls the model update with new fields."""
    script = """
import streamlit as st
from ui import changes

EVENTS_KEY = "__events"
CATS_KEY = "__cats"
UPD_KEY = "__update_calls"

if EVENTS_KEY not in st.session_state:
    st.session_state[EVENTS_KEY] = [
        {
            "id": "e1",
            "title": "Old title",
            "notes": "Old notes",
            "recorded_at": "2026-02-01T12:00:00Z",
            "category_id": "c1",
            "categories": {"name": "fitness"},
        }
    ]
if CATS_KEY not in st.session_state:
    st.session_state[CATS_KEY] = [{"id": "c1", "name": "fitness"}]
if UPD_KEY not in st.session_state:
    st.session_state[UPD_KEY] = []

def _get_categories():
    return st.session_state[CATS_KEY]

def _get_change_events(limit=200):
    return st.session_state[EVENTS_KEY]

def _update_change_event(event_id, payload):
    st.session_state[UPD_KEY].append((event_id, payload))
    for ev in st.session_state[EVENTS_KEY]:
        if ev["id"] == event_id:
            ev.update(payload)
            ev["categories"] = {"name": "fitness"}
    return {"data": [{"id": event_id}]}

changes.models.get_categories = _get_categories
changes.models.get_change_events = _get_change_events
changes.models.create_change_event = lambda payload: None
changes.models.delete_change_event = lambda _id: None
changes.models.update_change_event = _update_change_event

changes.show_changes()
"""

    at = AppTest.from_string(script)
    at.run()

    at.button[0].click()  # Edit
    at.run()

    # text_input[0] = create form title, text_input[1] = edit form title
    at.text_input[1].input("New title")
    at.text_area[1].input("New notes")
    at.form_submit_button[1].click()  # Save Changes
    at.run()

    calls = at.session_state.get("__update_calls", [])
    assert len(calls) == 1
    event_id, payload = calls[0]
    assert event_id == "e1"
    assert payload["title"] == "New title"
    assert payload["notes"] == "New notes"
    assert payload["category_id"] == "c1"
    assert "recorded_at" in payload
