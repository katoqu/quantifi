import importlib
import json
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


def test_init_session_state_respects_retry_config(monkeypatch):
    st = _install_streamlit_stub(
        monkeypatch,
        secrets={
            "AUTH_EVENT_LOG": False,
            "AUTH_COOKIE_RESTORE_RETRIES": 3,
            "AUTH_COOKIE_RESTORE_DELAY_SECONDS": 0.25,
        },
    )

    rerun_calls = {"count": 0}
    sleep_calls: list[float] = []

    class _Auth:
        def get_user(self):
            return None

    supabase_config = types.SimpleNamespace(
        sb=types.SimpleNamespace(auth=_Auth()),
        sb_admin=types.SimpleNamespace(auth=types.SimpleNamespace(admin=types.SimpleNamespace())),
    )
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)
    auth = _import_fresh("auth")
    auth.auth_persistence.mount = lambda: None
    auth.auth_persistence.inspect_state = lambda: {"reason": "cookie_missing"}
    auth.auth_persistence.load = lambda: None
    st.rerun = lambda: rerun_calls.__setitem__("count", rerun_calls["count"] + 1)
    monkeypatch.setattr(auth.time, "sleep", lambda secs: sleep_calls.append(secs))

    for _ in range(4):
        auth.init_session_state()

    assert rerun_calls["count"] == 3
    assert st.session_state["_restore_attempts"] == 3
    assert sleep_calls == [0.25, 0.25, 0.25]


def test_init_session_state_flags_transient_restore_error(monkeypatch):
    st = _install_streamlit_stub(monkeypatch, secrets={"AUTH_EVENT_LOG": False})

    class _Auth:
        def get_user(self):
            return None

    supabase_config = types.SimpleNamespace(
        sb=types.SimpleNamespace(auth=_Auth()),
        sb_admin=types.SimpleNamespace(auth=types.SimpleNamespace(admin=types.SimpleNamespace())),
    )
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)
    auth = _import_fresh("auth")
    auth.auth_persistence.mount = lambda: None
    auth.auth_persistence.inspect_state = lambda: {"reason": "cookie_present"}
    auth.auth_persistence.load = lambda: {"access_token": "a", "refresh_token": "r"}
    auth.AuthEngine.restore_session = staticmethod(
        lambda _a, _r: (None, None, "Connection timeout while waking app")
    )
    st.rerun = lambda: None
    monkeypatch.setattr(auth.time, "sleep", lambda _secs: None)

    auth.init_session_state()

    assert st.session_state["_cookie_restore_failed"] is True


def test_init_session_state_does_not_flag_invalid_expired_error(monkeypatch):
    st = _install_streamlit_stub(monkeypatch, secrets={"AUTH_EVENT_LOG": False})

    class _Auth:
        def get_user(self):
            return None

    supabase_config = types.SimpleNamespace(
        sb=types.SimpleNamespace(auth=_Auth()),
        sb_admin=types.SimpleNamespace(auth=types.SimpleNamespace(admin=types.SimpleNamespace())),
    )
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)
    auth = _import_fresh("auth")
    auth.auth_persistence.mount = lambda: None
    auth.auth_persistence.inspect_state = lambda: {"reason": "cookie_present"}
    auth.auth_persistence.load = lambda: {"access_token": "a", "refresh_token": "r"}
    auth.AuthEngine.restore_session = staticmethod(lambda _a, _r: (None, None, "JWT expired"))
    st.rerun = lambda: None
    monkeypatch.setattr(auth.time, "sleep", lambda _secs: None)

    auth.init_session_state()

    assert st.session_state["_cookie_restore_failed"] is False


def test_init_session_state_appends_structured_auth_debug_events(monkeypatch):
    st = _install_streamlit_stub(monkeypatch, secrets={"AUTH_EVENT_LOG": False})

    class _Auth:
        def get_user(self):
            return None

    supabase_config = types.SimpleNamespace(
        sb=types.SimpleNamespace(auth=_Auth()),
        sb_admin=types.SimpleNamespace(auth=types.SimpleNamespace(admin=types.SimpleNamespace())),
    )
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)
    auth = _import_fresh("auth")
    auth.auth_persistence.mount = lambda: None
    auth.auth_persistence.inspect_state = lambda: {"reason": "cookie_missing"}
    auth.auth_persistence.load = lambda: None
    st.rerun = lambda: None
    monkeypatch.setattr(auth.time, "sleep", lambda _secs: None)

    auth.init_session_state()

    logs = st.session_state.get("auth_debug", [])
    assert any(line.startswith("[init_session_state] ") for line in logs)
    assert any(line.startswith("[persistence_state] ") for line in logs)


def test_init_session_state_skips_file_logging_when_disabled(monkeypatch, tmp_path):
    log_path = tmp_path / "disabled-auth.jsonl"
    st = _install_streamlit_stub(
        monkeypatch,
        secrets={"AUTH_EVENT_LOG": False, "AUTH_EVENT_LOG_PATH": str(log_path)},
    )

    class _Auth:
        def get_user(self):
            return None

    supabase_config = types.SimpleNamespace(
        sb=types.SimpleNamespace(auth=_Auth()),
        sb_admin=types.SimpleNamespace(auth=types.SimpleNamespace(admin=types.SimpleNamespace())),
    )
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)
    auth = _import_fresh("auth")
    auth.auth_persistence.mount = lambda: None
    auth.auth_persistence.inspect_state = lambda: {"reason": "cookie_missing"}
    auth.auth_persistence.load = lambda: None
    st.rerun = lambda: None
    monkeypatch.setattr(auth.time, "sleep", lambda _secs: None)

    auth.init_session_state()

    assert not log_path.exists()


def test_init_session_state_writes_file_log_when_enabled(monkeypatch, tmp_path):
    log_path = tmp_path / "custom-auth-events.jsonl"
    st = _install_streamlit_stub(
        monkeypatch,
        secrets={"AUTH_EVENT_LOG": True, "AUTH_EVENT_LOG_PATH": str(log_path)},
    )

    class _Auth:
        def get_user(self):
            return None

    supabase_config = types.SimpleNamespace(
        sb=types.SimpleNamespace(auth=_Auth()),
        sb_admin=types.SimpleNamespace(auth=types.SimpleNamespace(admin=types.SimpleNamespace())),
    )
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)
    auth = _import_fresh("auth")
    auth.auth_persistence.mount = lambda: None
    auth.auth_persistence.inspect_state = lambda: {"reason": "cookie_missing"}
    auth.auth_persistence.load = lambda: None
    st.rerun = lambda: None
    monkeypatch.setattr(auth.time, "sleep", lambda _secs: None)

    auth.init_session_state()

    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert lines
    first = json.loads(lines[0])
    assert first["event"] == "init_session_state"


def test_auth_page_reconnect_path_clears_flag_on_click(monkeypatch):
    st = _install_streamlit_stub(monkeypatch, secrets={"AUTH_EVENT_LOG": False})
    rerun_calls = {"count": 0}
    warning_calls = {"count": 0}

    sb = types.SimpleNamespace(auth=types.SimpleNamespace())
    sb_admin = types.SimpleNamespace(auth=types.SimpleNamespace(admin=types.SimpleNamespace()))
    supabase_config = types.SimpleNamespace(sb=sb, sb_admin=sb_admin)
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)
    auth = _import_fresh("auth")

    st.session_state["app_just_woke_up"] = False
    st.session_state["_cookie_restore_failed"] = True
    st.rerun = lambda: rerun_calls.__setitem__("count", rerun_calls["count"] + 1)
    st.warning = lambda *_a, **_k: warning_calls.__setitem__("count", warning_calls["count"] + 1)
    st.button = lambda label, **_kwargs: label == "🔄 Reconnect"

    auth.auth_page()

    assert warning_calls["count"] == 1
    assert st.session_state["_cookie_restore_failed"] is False
    assert rerun_calls["count"] == 1
