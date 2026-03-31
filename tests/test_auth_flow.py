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


def _install_streamlit_stub(monkeypatch, *, secrets: dict | None = None):
    st = types.SimpleNamespace()
    st.secrets = dict(secrets or {})
    st.session_state = _AttrDict()
    st.query_params = _AttrDict()

    def _no_op(*_a, **_k):
        return None

    class _MockContextManager:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    st.error = _no_op
    st.rerun = _no_op
    st.spinner = lambda *_a, **_k: _MockContextManager()
    st.title = _no_op
    st.warning = _no_op
    st.caption = _no_op
    st.subheader = _no_op

    monkeypatch.setitem(sys.modules, "streamlit", st)
    return st


def _import_fresh(name: str):
    sys.modules.pop(name, None)
    return importlib.import_module(name)


def test_is_authenticated_respects_recovery_flag(monkeypatch):
    st = _install_streamlit_stub(monkeypatch)

    sb = types.SimpleNamespace(auth=types.SimpleNamespace())
    sb_admin = types.SimpleNamespace(auth=types.SimpleNamespace(admin=types.SimpleNamespace()))
    supabase_config = types.SimpleNamespace(sb=sb, sb_admin=sb_admin)
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)

    sys.modules.pop("auth_ui", None)
    auth = _import_fresh("auth")

    st.session_state.user = types.SimpleNamespace(id="u1")
    st.session_state.show_recovery_form = True

    assert auth.is_authenticated() is False


def test_is_admin_checks_admin_emails(monkeypatch):
    st = _install_streamlit_stub(monkeypatch, secrets={"ADMIN_EMAILS": "a@example.com, b@example.com"})

    sb = types.SimpleNamespace(auth=types.SimpleNamespace())
    sb_admin = types.SimpleNamespace(auth=types.SimpleNamespace(admin=types.SimpleNamespace()))
    supabase_config = types.SimpleNamespace(sb=sb, sb_admin=sb_admin)
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)

    sys.modules.pop("auth_ui", None)
    auth = _import_fresh("auth")

    st.session_state.user = types.SimpleNamespace(email="a@example.com")
    assert auth.is_admin() is True

    st.session_state.user = types.SimpleNamespace(email="c@example.com")
    assert auth.is_admin() is False


def test_sign_out_clears_state(monkeypatch):
    st = _install_streamlit_stub(monkeypatch)

    calls = {"sign_out": 0, "clear": 0, "bump": 0}

    class _Auth:
        def sign_out(self):
            calls["sign_out"] += 1

    sb = types.SimpleNamespace(auth=_Auth())
    sb_admin = types.SimpleNamespace(auth=types.SimpleNamespace(admin=types.SimpleNamespace()))
    supabase_config = types.SimpleNamespace(sb=sb, sb_admin=sb_admin)
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)

    auth = _import_fresh("auth")

    auth.auth_persistence.clear = lambda: calls.__setitem__("clear", calls["clear"] + 1)
    auth.cache_control.bump = lambda: calls.__setitem__("bump", calls["bump"] + 1)

    st.session_state.user = types.SimpleNamespace(id="u1")
    st.session_state.show_recovery_form = True
    st.session_state.show_password_reset = True

    auth.sign_out()

    assert calls["sign_out"] == 1
    assert calls["clear"] == 1
    assert calls["bump"] == 1
    assert st.session_state.user is None
    assert st.session_state["_logout_pending"] is True
    assert st.session_state.show_recovery_form is False
    assert st.session_state.show_password_reset is False


def test_handle_link_tokens_code_error(monkeypatch):
    st = _install_streamlit_stub(monkeypatch)

    sb = types.SimpleNamespace(auth=types.SimpleNamespace())
    sb_admin = types.SimpleNamespace(auth=types.SimpleNamespace(admin=types.SimpleNamespace()))
    supabase_config = types.SimpleNamespace(sb=sb, sb_admin=sb_admin)
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)

    auth = _import_fresh("auth")

    auth.auth_persistence.mount = lambda: None
    auth.init_session_state()
    st.query_params["code"] = "abc"
    st.query_params["type"] = "recovery"

    auth.AuthEngine.exchange_code_for_session = staticmethod(lambda _c: (None, None, "bad"))

    assert auth.handle_link_tokens() is True
    assert st.query_params == {}
    assert st.session_state.get("show_recovery_form") is False


def test_init_session_state_proactive_refresh(monkeypatch):
    st = _install_streamlit_stub(monkeypatch)

    class _Auth:
        def get_user(self):
            return None

    sb = types.SimpleNamespace(auth=_Auth())
    sb_admin = types.SimpleNamespace(auth=types.SimpleNamespace(admin=types.SimpleNamespace()))
    supabase_config = types.SimpleNamespace(sb=sb, sb_admin=sb_admin)
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)

    auth = _import_fresh("auth")

    auth.auth_persistence.mount = lambda: None
    st.session_state.user = types.SimpleNamespace(id="u1")
    auth.AuthEngine.maybe_refresh_session = staticmethod(
        lambda seconds_skew=900: ({"access_token": "a", "refresh_token": "r"}, None)
    )
    auth.AuthEngine.session_to_payload = staticmethod(lambda _s: {"access_token": "a", "refresh_token": "r"})

    saved = {"count": 0}
    auth.auth_persistence.save_tokens = lambda a, r: saved.__setitem__("count", saved["count"] + 1)

    auth.init_session_state()

    assert saved["count"] == 1
