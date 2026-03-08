import importlib
import sys
import types


class _AttrDict(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e

    def __setattr__(self, name, value):
        self[name] = value


def _import_fresh(name: str):
    sys.modules.pop(name, None)
    return importlib.import_module(name)

def _install_streamlit_stub(monkeypatch, *, secrets: dict | None = None):
    st = types.SimpleNamespace()
    st.secrets = dict(secrets or {})
    st.session_state = _AttrDict()
    st.query_params = _AttrDict()

    def _no_op(*_a, **_k):
        return None
    
    # NEW: Context manager stub for st.spinner
    class _MockContextManager:
        def __enter__(self): return self
        def __exit__(self, *args): pass

    def _spinner_mock(*_a, **_k):
        return _MockContextManager()

    # Stubs required by the new auth.py logic
    st.error = _no_op
    st.rerun = _no_op     # <--- This fixes your AttributeError
    st.spinner = _spinner_mock # <--- This prevents failures in auth_page
    st.title = _no_op
    st.warning = _no_op

    monkeypatch.setitem(sys.modules, "streamlit", st)
    return st


def test_invite_link_logs_in_without_password_prompt(monkeypatch):
    """
    Regression: Supabase invite links should not force the "set password" flow when
    the app supports passwordless login via magic links.
    """
    st = _install_streamlit_stub(monkeypatch, secrets={})

    class _Auth:
        def verify_otp(self, payload):
            assert payload["type"] == "invite"
            return {
                "user": types.SimpleNamespace(id="u1", email="a@example.com"),
                "session": {"access_token": "a", "refresh_token": "r"},
            }

    sb = types.SimpleNamespace(auth=_Auth())
    sb_admin = types.SimpleNamespace(auth=types.SimpleNamespace(admin=types.SimpleNamespace()))
    supabase_config = types.SimpleNamespace(sb=sb, sb_admin=sb_admin)
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)

    auth = _import_fresh("auth")

    auth.init_session_state()
    st.query_params["token_hash"] = "th"
    st.query_params["type"] = "invite"

    assert auth.handle_link_tokens() is True
    assert st.query_params == {}
    assert st.session_state.get("show_recovery_form") is False
    assert st.session_state.get("user") is not None
    assert getattr(st.session_state["user"], "email", None) == "a@example.com"


def test_recovery_link_shows_password_reset_form(monkeypatch):
    st = _install_streamlit_stub(monkeypatch, secrets={})

    class _Auth:
        def verify_otp(self, payload):
            assert payload["type"] == "recovery"
            return {"user": None, "session": None}

    sb = types.SimpleNamespace(auth=_Auth())
    sb_admin = types.SimpleNamespace(auth=types.SimpleNamespace(admin=types.SimpleNamespace()))
    supabase_config = types.SimpleNamespace(sb=sb, sb_admin=sb_admin)
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)

    auth = _import_fresh("auth")

    auth.init_session_state()
    st.query_params["token_hash"] = "th"
    st.query_params["type"] = "recovery"

    assert auth.handle_link_tokens() is True
    assert st.session_state.get("show_recovery_form") is True
    assert st.session_state.get("recovery_type") == "recovery"

