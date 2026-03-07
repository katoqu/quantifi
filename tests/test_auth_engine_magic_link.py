import importlib
import sys
import types


def _import_fresh(name: str):
    sys.modules.pop(name, None)
    return importlib.import_module(name)


def _install_streamlit_stub(monkeypatch, *, secrets: dict):
    st = types.SimpleNamespace()
    st.secrets = dict(secrets)
    monkeypatch.setitem(sys.modules, "streamlit", st)
    return st


def test_send_magic_link_tries_payload_variants(monkeypatch):
    """
    The Supabase Python client has had multiple payload shapes for sign_in_with_otp.
    Ensure we try variants and succeed when one matches.
    """
    _install_streamlit_stub(monkeypatch, secrets={"REDIRECT_URL": "http://localhost:8501"})

    calls: list[dict] = []

    class _Auth:
        def sign_in_with_otp(self, payload):
            calls.append(payload)
            # Only accept the last fallback shape to prove we try multiple variants.
            if payload.get("redirect_to") == "http://localhost:8501" and payload.get("email") == "a@example.com":
                return {"ok": True}
            raise RuntimeError("unsupported payload shape")

    sb = types.SimpleNamespace(auth=_Auth())
    sb_admin = types.SimpleNamespace(auth=types.SimpleNamespace(admin=types.SimpleNamespace()))
    supabase_config = types.SimpleNamespace(sb=sb, sb_admin=sb_admin)
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)

    auth_engine = _import_fresh("auth_engine")

    ok, err = auth_engine.AuthEngine.send_magic_link("A@EXAMPLE.COM")
    assert ok is True
    assert err is None
    assert len(calls) >= 2
    assert calls[-1] == {"email": "a@example.com", "redirect_to": "http://localhost:8501"}

