import importlib
import sys
import types

import pytest


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


def _install_streamlit_stub(monkeypatch, *, secrets: dict):
    st = types.SimpleNamespace()
    st.secrets = dict(secrets)
    st.session_state = _AttrDict()
    st.query_params = _AttrDict()
    monkeypatch.setitem(sys.modules, "streamlit", st)
    return st


def _install_cookie_manager_stub(monkeypatch):
    class CookieManager:
        def __init__(self, key=None):
            self._cookies = {}
            self.key = key

        def get(self, key):
            return self._cookies.get(key)

        def set(self, key, value, expires_at=None):
            _ = expires_at
            self._cookies[key] = value

        def delete(self, key):
            self._cookies.pop(key, None)
        
        def get_all(self):
            return self._cookies

    stx = types.SimpleNamespace(CookieManager=CookieManager)
    monkeypatch.setitem(sys.modules, "extra_streamlit_components", stx)
    return stx


def test_auth_persistence_roundtrip_tokens(monkeypatch):
    _install_streamlit_stub(monkeypatch, secrets={"PERSIST_LOGIN": True})
    _install_cookie_manager_stub(monkeypatch)

    auth_persistence = _import_fresh("auth_persistence")

    assert auth_persistence.save_tokens("access-token-123", "refresh-token-456", max_age_days=7) is True
    loaded = auth_persistence.load()
    assert loaded is not None
    assert loaded["access_token"] == "access-token-123"
    assert loaded["refresh_token"] == "refresh-token-456"

    assert auth_persistence.clear() is True
    assert auth_persistence.load() is None


def test_auth_persistence_loads_legacy_token_payload(monkeypatch):
    _install_streamlit_stub(monkeypatch, secrets={"PERSIST_LOGIN": True})
    _install_cookie_manager_stub(monkeypatch)

    auth_persistence = _import_fresh("auth_persistence")

    cm = auth_persistence._cookie_manager()
    legacy = {"access_token": "a", "refresh_token": "r", "expires_at": 123}
    cm.set(auth_persistence.COOKIE_NAME, auth_persistence._encode(legacy), expires_at=30)

    out = auth_persistence.load()
    assert isinstance(out, dict)
    assert out["access_token"] == "a"
    assert out["refresh_token"] == "r"


def test_session_store_encrypts_server_side(monkeypatch):
    pytest.importorskip("cryptography")
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode("utf-8")
    _install_streamlit_stub(
        monkeypatch,
        secrets={
            "PERSIST_LOGIN": True,
            "SESSION_ENC_KEY": key,
            "SUPABASE_SERVICE_ROLE_KEY": "service-role",
        },
    )

    # Stub supabase_config.sb_admin with an in-memory table.
    store: dict[str, dict] = {}

    class _Result:
        def __init__(self, data=None):
            self.data = data or []

    class _Table:
        def __init__(self, name: str):
            self._name = name
            self._op = None
            self._payload = None
            self._filters = {}
            self._limit = None
            self._select_cols = None

        def insert(self, payload):
            self._op = "insert"
            self._payload = payload
            return self

        def update(self, payload):
            self._op = "update"
            self._payload = payload
            return self

        def select(self, cols):
            self._op = "select"
            self._select_cols = cols
            return self

        def eq(self, key, value):
            self._filters[key] = ("eq", value)
            return self

        def is_(self, key, value):
            self._filters[key] = ("is", value)
            return self

        def limit(self, n):
            self._limit = n
            return self

        def execute(self):
            assert self._name == "app_sessions"
            if self._op == "insert":
                row = dict(self._payload)
                store[row["id"]] = row
                return _Result([row])

            if self._op == "update":
                # Only support filters used in code: id eq + revoked_at is null.
                sid = self._filters.get("id", (None, None))[1]
                row = store.get(sid)
                if not row:
                    return _Result([])
                if ("revoked_at" in self._filters) and self._filters["revoked_at"] == ("is", "null"):
                    if row.get("revoked_at") is not None:
                        return _Result([])
                row.update(self._payload or {})
                return _Result([row])

            if self._op == "select":
                sid = self._filters.get("id", (None, None))[1]
                row = store.get(sid)
                if not row:
                    return _Result([])
                return _Result([row])

            raise AssertionError(f"Unsupported op: {self._op}")

    class _SbAdmin:
        def table(self, name: str):
            return _Table(name)

    supabase_config = types.SimpleNamespace(sb_admin=_SbAdmin())
    monkeypatch.setitem(sys.modules, "supabase_config", supabase_config)

    session_store = _import_fresh("session_store")

    payload = {"access_token": "a1", "refresh_token": "r1", "expires_at": 999}
    sid = session_store.create_session(user_id="u1", session_payload=payload, max_age_days=30)
    assert isinstance(sid, str) and sid

    loaded = session_store.load_session_payload(sid)
    assert loaded == payload

    updated = {"access_token": "a2", "refresh_token": "r2"}
    assert session_store.update_session(sid=sid, session_payload=updated) is True
    assert session_store.load_session_payload(sid) == updated

    assert session_store.revoke_session(sid) is True
    assert session_store.load_session_payload(sid) is None
