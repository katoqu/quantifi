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


def test_auth_event_store_disabled_no_write(monkeypatch):
    _install_streamlit_stub(monkeypatch, secrets={"AUTH_EVENT_LOG_DB": False})

    calls = {"count": 0}

    class _Table:
        def insert(self, _row):
            calls["count"] += 1
            return self
        def execute(self):
            return None

    supabase_config = types.SimpleNamespace(sb_admin=types.SimpleNamespace(table=lambda _name: _Table()))
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)
    mod = _import_fresh("auth_event_store")

    mod.write_event(event="x", payload={"a": 1})
    assert calls["count"] == 0


def test_auth_event_store_enabled_writes_row(monkeypatch):
    _install_streamlit_stub(
        monkeypatch,
        secrets={"AUTH_EVENT_LOG_DB": True, "AUTH_EVENT_LOG_TABLE": "auth_event_logs", "ENV_NAME": "prod"},
    )

    seen = {"table": None, "row": None}

    class _Table:
        def insert(self, row):
            seen["row"] = row
            return self
        def execute(self):
            return None

    def _table(name: str):
        seen["table"] = name
        return _Table()

    supabase_config = types.SimpleNamespace(sb_admin=types.SimpleNamespace(table=_table))
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)
    mod = _import_fresh("auth_event_store")

    mod.write_event(event="cookie_restore_ok", payload={"event": "cookie_restore_ok"}, user_id="u1", sid="s1")

    assert seen["table"] == "auth_event_logs"
    assert seen["row"]["env"] == "prod"
    assert seen["row"]["event"] == "cookie_restore_ok"
    assert seen["row"]["user_id"] == "u1"
    assert seen["row"]["sid"] == "s1"
    assert isinstance(seen["row"]["payload"], dict)
    assert "created_at" in seen["row"]

