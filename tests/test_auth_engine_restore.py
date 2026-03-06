import importlib
import sys
import types

import pytest


def _install_streamlit_stub(monkeypatch):
    st = types.SimpleNamespace()
    st.secrets = {}
    monkeypatch.setitem(sys.modules, "streamlit", st)
    return st


def _import_fresh(name: str):
    sys.modules.pop(name, None)
    return importlib.import_module(name)


def test_restore_session_refresh_fallback(monkeypatch):
    """
    If initial set_session fails (e.g., expired access token), AuthEngine.restore_session
    falls back to refresh_session and then sets the new session.
    """
    _install_streamlit_stub(monkeypatch)

    calls = {"set": [], "refresh": []}

    class _Auth:
        def set_session(self, access_token, refresh_token):
            calls["set"].append((access_token, refresh_token))
            if access_token == "expired":
                raise RuntimeError("JWT expired")
            return {"user": {"id": "u1"}, "session": {"access_token": access_token, "refresh_token": refresh_token}}

        def refresh_session(self, refresh_token=None):
            calls["refresh"].append(refresh_token)
            return {"session": {"access_token": "new_access", "refresh_token": "new_refresh"}}

    sb = types.SimpleNamespace(auth=_Auth())
    sb_admin = types.SimpleNamespace(auth=types.SimpleNamespace(admin=types.SimpleNamespace()))
    supabase_config = types.SimpleNamespace(sb=sb, sb_admin=sb_admin)
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)

    auth_engine = _import_fresh("auth_engine")

    user, session, err = auth_engine.AuthEngine.restore_session("expired", "r1")
    assert err is None
    assert user == {"id": "u1"}
    assert session["access_token"] == "new_access"
    assert calls["refresh"] == ["r1"]
    # Called twice: once failing, once after refresh
    assert calls["set"] == [("expired", "r1"), ("new_access", "new_refresh")]

