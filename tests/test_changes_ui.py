"""Streamlit UI tests for the Lifestyle Changes feature."""

import pytest


st = pytest.importorskip("streamlit")
AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


def _widget_label(widget) -> str:
    return str(
        getattr(widget, "label", None)
        or getattr(widget, "value", None)
        or getattr(widget, "name", None)
        or ""
    )


def _widget_key(widget):
    return getattr(widget, "key", None)


def _find_widget(widgets, *, label: str | None = None, key: str | None = None):
    for w in widgets:
        if label is not None and _widget_label(w) != label:
            continue
        if key is not None and _widget_key(w) != key:
            continue
        return w
    raise AssertionError(f"Widget not found (label={label!r}, key={key!r}).")


def _click_button(at: AppTest, *, label: str | None = None, key: str | None = None):
    btn = _find_widget(at.button, label=label, key=key)
    btn.click()


def _input_text(at: AppTest, *, label: str | None = None, key: str | None = None, value: str):
    w = _find_widget(at.text_input, label=label, key=key)
    w.input(value)


def _input_area(at: AppTest, *, label: str | None = None, key: str | None = None, value: str):
    w = _find_widget(at.text_area, label=label, key=key)
    w.input(value)


def _session_get(at: AppTest, key: str, default):
    try:
        return at.session_state[key]
    except Exception:
        return default


def test_changes_can_create_event():
    """Creating a change event calls the model with category + title + notes."""
    script = """
import streamlit as st
from ui import changes
import datetime as dt

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

# Streamlit testing can be sensitive to some newer widgets; keep this test focused.
# In particular, some Streamlit versions have issues serializing `st.pills` state under AppTest.
changes.st.pills = lambda *a, **k: "Today"
changes.st.date_input = lambda *a, **k: dt.date.today()
changes.st.time_input = lambda *a, **k: dt.datetime.now().time().replace(second=0, microsecond=0)

changes.show_changes()
"""

    at = AppTest.from_string(script)
    at.run()

    _input_text(at, label="Title", value="Started vegetarian nutrition")
    _input_area(at, label="Notes (Markdown supported)", value="No meat, fish ok.")
    _click_button(at, label="Add Change")
    at.run()

    calls = _session_get(at, "__create_calls", [])
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
import datetime as dt

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

# Streamlit testing can be sensitive to some newer widgets; keep this test focused.
# In particular, some Streamlit versions have issues serializing `st.pills` state under AppTest.
changes.st.pills = lambda *a, **k: "Today"
changes.st.date_input = lambda *a, **k: dt.date(2026, 2, 1)
changes.st.time_input = lambda *a, **k: dt.time(12, 0)

changes.show_changes()
"""

    at = AppTest.from_string(script)
    at.run()

    try:
        _click_button(at, key="edit_change_e1")
    except AssertionError:
        _click_button(at, label="Edit")
    at.run()

    _input_text(at, key="edit_change_title_e1", value="New title")
    _input_area(at, key="edit_change_notes_e1", value="New notes")
    _click_button(at, label="Save Changes")
    at.run()

    calls = _session_get(at, "__update_calls", [])
    assert len(calls) == 1
    event_id, payload = calls[0]
    assert event_id == "e1"
    assert payload["title"] == "New title"
    assert payload["notes"] == "New notes"
    assert payload["category_id"] == "c1"
    assert "recorded_at" in payload


def test_changes_can_end_routine_and_archive():
    """Ending an active routine sets end_at and archives the event."""
    script = """
import streamlit as st
from ui import changes
import datetime as dt

EVENTS_KEY = "__events"
CATS_KEY = "__cats"
UPD_KEY = "__update_calls"

if EVENTS_KEY not in st.session_state:
    st.session_state[EVENTS_KEY] = [
        {
            "id": "e1",
            "title": "Morning walk",
            "notes": "30 min",
            "recorded_at": "2026-02-01T12:00:00Z",
            "end_at": None,
            "is_archived": False,
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

changes.st.pills = lambda *a, **k: "Today"
changes.st.date_input = lambda *a, **k: dt.date(2026, 2, 5)
changes.st.time_input = lambda *a, **k: dt.time(9, 30)

changes.show_changes()
"""

    at = AppTest.from_string(script)
    at.run()

    _click_button(at, key="end_change_e1")
    at.run()

    _click_button(at, label="Confirm End Date")
    at.run()

    calls = _session_get(at, "__update_calls", [])
    assert len(calls) == 1
    event_id, payload = calls[0]
    assert event_id == "e1"
    assert payload["is_archived"] is True
    assert "end_at" in payload


def test_changes_can_revive_archived_routine():
    """Reviving an archived routine clears end_at and sets a new start date."""
    script = """
import streamlit as st
from ui import changes
import datetime as dt

EVENTS_KEY = "__events"
CATS_KEY = "__cats"
UPD_KEY = "__update_calls"

if EVENTS_KEY not in st.session_state:
    st.session_state[EVENTS_KEY] = [
        {
            "id": "e1",
            "title": "Morning walk",
            "notes": "30 min",
            "recorded_at": "2026-02-01T12:00:00Z",
            "end_at": "2026-02-10T12:00:00Z",
            "is_archived": True,
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

changes.st.pills = lambda *a, **k: "Today"
changes.st.date_input = lambda *a, **k: dt.date(2026, 2, 20)
changes.st.time_input = lambda *a, **k: dt.time(8, 15)

changes.show_changes()
"""

    at = AppTest.from_string(script)
    at.session_state["show_archived_changes"] = True
    at.run()

    _click_button(at, key="revive_change_e1")
    at.run()

    _click_button(at, label="Confirm New Start Date")
    at.run()

    calls = _session_get(at, "__update_calls", [])
    assert len(calls) == 1
    event_id, payload = calls[0]
    assert event_id == "e1"
    assert payload["is_archived"] is False
    assert payload["end_at"] is None
    assert "recorded_at" in payload
