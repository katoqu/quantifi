import importlib
import sys
import types


def _import_fresh(name: str):
    sys.modules.pop(name, None)
    return importlib.import_module(name)


def _install_streamlit_stub(monkeypatch, *, secrets: dict | None = None):
    st = types.SimpleNamespace()
    st.secrets = dict(secrets or {})
    monkeypatch.setitem(sys.modules, "streamlit", st)
    return st


def test_exchange_code_for_session_tries_payload_variants(monkeypatch):
    _install_streamlit_stub(monkeypatch, secrets={})

    calls: list[object] = []

    class _Auth:
        def exchange_code_for_session(self, payload):
            calls.append(payload)
            if payload == {"code": "abc"}:
                return {
                    "user": types.SimpleNamespace(id="u1", email="a@example.com"),
                    "session": {"access_token": "a", "refresh_token": "r"},
                }
            raise TypeError("unsupported payload shape")

    sb = types.SimpleNamespace(auth=_Auth())
    sb_admin = types.SimpleNamespace(auth=types.SimpleNamespace(admin=types.SimpleNamespace()))
    supabase_config = types.SimpleNamespace(sb=sb, sb_admin=sb_admin)
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)

    auth_engine = _import_fresh("auth_engine")

    user, session, err = auth_engine.AuthEngine.exchange_code_for_session("abc")
    assert err is None
    assert user is not None
    assert session is not None
    assert len(calls) >= 2
    assert calls[-1] == {"code": "abc"}


def test_exchange_code_for_session_missing_code(monkeypatch):
    _install_streamlit_stub(monkeypatch, secrets={})

    sb = types.SimpleNamespace(auth=types.SimpleNamespace())
    sb_admin = types.SimpleNamespace(auth=types.SimpleNamespace(admin=types.SimpleNamespace()))
    supabase_config = types.SimpleNamespace(sb=sb, sb_admin=sb_admin)
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)

    auth_engine = _import_fresh("auth_engine")

    user, session, err = auth_engine.AuthEngine.exchange_code_for_session("   ")
    assert user is None
    assert session is None
    assert err is not None
