import importlib
import types
import sys
import time
import pytest
import streamlit as st

import importlib
import types
import sys
import time
import pytest
import streamlit as st

# You need these two because they are used by _install_streamlit_stub
class _AttrDict(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e
    def __setattr__(self, name, value):
        self[name] = value

def _install_streamlit_stub(monkeypatch, *, secrets: dict | None = None):
    st_mock = types.SimpleNamespace()
    st_mock.secrets = dict(secrets or {})
    st_mock.session_state = _AttrDict()
    st_mock.query_params = _AttrDict()

    def _no_op(*_a, **_k): return None
    
    class _MockContextManager:
        def __enter__(self): return self
        def __exit__(self, *args): pass

    st_mock.error = _no_op
    st_mock.rerun = _no_op
    st_mock.spinner = lambda *_a, **_k: _MockContextManager()
    st_mock.title = _no_op
    st_mock.warning = _no_op

    monkeypatch.setitem(sys.modules, "streamlit", st_mock)
    return st_mock

def test_init_session_state_retries_on_missing_cookie(monkeypatch):
    """Ensures init_session_state waits for cookies before failing."""
    st = _install_streamlit_stub(monkeypatch)
    
    # Track how many times rerun is called
    rerun_counter = {"count": 0}
    def mock_rerun():
        rerun_counter["count"] += 1
    st.rerun = mock_rerun

    # Mock auth_persistence to return None (simulating a slow-loading cookie)
    monkeypatch.setattr("auth_persistence.load", lambda: None)
    
    import auth
    importlib.reload(auth)
    
    auth.init_session_state()
    
    # Verify the "Bridge" triggered the rerun to wait for the cookie
    assert st.session_state._restore_attempts == 1
    assert rerun_counter["count"] == 1

def test_restore_session_retries_on_network_error(monkeypatch):
    """Verifies that restore_session retries on transient network blips."""
    
    # 1. Setup the Stub for Streamlit
    _install_streamlit_stub(monkeypatch)
    
    # 2. Define the Mock behavior
    call_count = {"count": 0}

    def mock_set_session_fail_then_pass(*args, **kwargs):
        call_count["count"] += 1
        if call_count["count"] < 2:
            # Simulate a temporary network drop during mobile wake-up
            raise Exception("Connection timeout") 
        # Return a mock successful response
        return types.SimpleNamespace(
            user=types.SimpleNamespace(id="u123", email="test@example.com"),
            session=types.SimpleNamespace(access_token="abc", refresh_token="def")
        )

    # 3. Create a fake Supabase client and inject it
    mock_sb = types.SimpleNamespace(auth=types.SimpleNamespace())
    mock_sb.auth.set_session = mock_set_session_fail_then_pass
    
    # Mock the config module that auth_engine imports from
    mock_config = types.SimpleNamespace(sb=mock_sb, sb_admin=types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "supabase_config", mock_config)
    
    # 4. CRITICAL: Force a fresh import of AuthEngine so it uses the mock
    if "auth_engine" in sys.modules:
        del sys.modules["auth_engine"]
    from auth_engine import AuthEngine
    
    # 5. Execute with a short delay for testing speed
    user, session, err = AuthEngine.restore_session("token", "refresh")
    
    # 6. Verify
    assert call_count["count"] == 2, "AuthEngine should have retried the network call"
    assert user is not None
    assert err is None