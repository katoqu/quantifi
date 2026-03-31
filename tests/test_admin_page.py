from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import pytest


st = pytest.importorskip("streamlit")
AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

if TYPE_CHECKING:
    from streamlit.testing.v1 import AppTest


def _widget_label(widget) -> str:
    return str(
        getattr(widget, "label", None)
        or getattr(widget, "value", None)
        or getattr(widget, "name", None)
        or ""
    )


def _widget_key(widget):
    return getattr(widget, "key", None)


def _find_widget(widgets, *, label: Optional[str] = None, key: Optional[str] = None):
    for w in widgets:
        if label is not None and _widget_label(w) != label:
            continue
        if key is not None and _widget_key(w) != key:
            continue
        return w
    raise AssertionError(f"Widget not found (label={label!r}, key={key!r}).")


def _click_button(at: AppTest, *, label: Optional[str] = None, key: Optional[str] = None):  # type: ignore
    btn = _find_widget(at.button, label=label, key=key)
    btn.click()


def _input_text(at: AppTest, *, label: Optional[str] = None, key: Optional[str] = None, value: str):  # type: ignore
    w = _find_widget(at.text_input, label=label, key=key)
    w.input(value)


def _session_get(at: AppTest, key: str, default):  # type: ignore
    try:
        return at.session_state[key]
    except Exception:
        return default


def test_admin_page_allowlist_flow():
    script = """
import streamlit as st
import types
import sys
import importlib

for name in ("ui.admin_page", "auth", "auth_engine", "auth_ui", "auth_persistence", "cache_control"):
    sys.modules.pop(name, None)
importlib.invalidate_caches()

import auth
from auth_engine import AuthEngine
from ui import admin_page

CALLS_KEY = "__admin_calls"
if CALLS_KEY not in st.session_state:
    st.session_state[CALLS_KEY] = {"allowlist": []}

def _fake_is_admin():
    return True

def _fake_add_allowlist(email):
    st.session_state[CALLS_KEY]["allowlist"].append(email)
    return True, None

auth.is_admin = _fake_is_admin
AuthEngine.add_allowlist_email = staticmethod(_fake_add_allowlist)

admin_page.render_admin_page()
"""

    at = AppTest.from_string(script)
    at.run()

    _input_text(at, label="Allowlist email", value="a@example.com")
    _click_button(at, label="Approve Signup")
    at.run()

    calls = _session_get(at, "__admin_calls", {})
    assert calls["allowlist"] == ["a@example.com"]
