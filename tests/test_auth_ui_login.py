from __future__ import annotations

from typing import TYPE_CHECKING, Optional

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


def test_login_ui_calls_password_sign_in():
    """
    Test that the login form captures email and password, calls sign_in,
    and sets user in session state on success.
    """
    script = """
import streamlit as st
import types
import sys
import importlib

# Other unit tests may import `auth_ui` while stubbing Streamlit. Ensure we load a
# fresh copy here so `auth_ui.st` is the real Streamlit module.
for name in ("auth_ui", "auth_engine", "auth_persistence", "cache_control", "session_store"):
    sys.modules.pop(name, None)
importlib.invalidate_caches()
import auth_ui

CALLS_KEY = "__auth_calls"
if CALLS_KEY not in st.session_state:
    st.session_state[CALLS_KEY] = {"sign_in": []}

def _fake_sign_in(email, password):
    st.session_state[CALLS_KEY]["sign_in"].append((email, password))
    # return a minimal (user, session, err) triple
    return types.SimpleNamespace(id="u1", email=email), {"access_token": "a", "refresh_token": "r"}, None

auth_ui.AuthEngine.sign_in = staticmethod(_fake_sign_in)

auth_ui.AuthUI.render_login_tab()
"""

    at = AppTest.from_string(script)
    at.run()

    # Basic presence checks
    assert any(_widget_label(w) == "Email" for w in at.text_input)
    assert any(_widget_label(w) == "Password" for w in at.text_input)
    assert any(_widget_label(w) == "Sign in" for w in at.button)

    _input_text(at, label="Email", value="a@example.com")
    _input_text(at, label="Password", value="secret")
    _click_button(at, label="Sign in")
    at.run()

    calls = _session_get(at, "__auth_calls", {})
    assert calls["sign_in"] == [("a@example.com", "secret")]
    assert _session_get(at, "user", None) is not None
