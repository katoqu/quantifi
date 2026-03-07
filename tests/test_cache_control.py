import pytest
import sys
import types
import importlib


def _install_streamlit_stub(monkeypatch):
    """Install a minimal streamlit stub to allow module imports."""
    st = types.SimpleNamespace()
    st.session_state = {}
    monkeypatch.setitem(sys.modules, "streamlit", st)
    return st


def _import_fresh(name: str):
    """Import a module fresh, reloading it."""
    sys.modules.pop(name, None)
    return importlib.import_module(name)


def test_cache_control_get_buster_returns_zero_by_default(monkeypatch):
    """Cache buster returns 0 when not set in session state."""
    st = _install_streamlit_stub(monkeypatch)
    cache_control = _import_fresh("cache_control")

    assert cache_control.get_buster() == 0


def test_cache_control_get_buster_returns_stored_value(monkeypatch):
    """Cache buster returns the value stored in session state."""
    st = _install_streamlit_stub(monkeypatch)
    st.session_state["cache_buster"] = 42
    cache_control = _import_fresh("cache_control")

    assert cache_control.get_buster() == 42


def test_cache_control_get_buster_handles_invalid_value(monkeypatch):
    """Cache buster returns 0 when value can't be converted to int."""
    st = _install_streamlit_stub(monkeypatch)
    st.session_state["cache_buster"] = "not a number"
    cache_control = _import_fresh("cache_control")

    assert cache_control.get_buster() == 0


def test_cache_control_bump_increments_cache_buster(monkeypatch):
    """Bumping cache buster increments the value in session state."""
    st = _install_streamlit_stub(monkeypatch)
    st.session_state["cache_buster"] = 5
    cache_control = _import_fresh("cache_control")

    result = cache_control.bump()
    assert result == 6
    assert st.session_state["cache_buster"] == 6


def test_cache_control_bump_increments_from_zero(monkeypatch):
    """Bumping cache buster starts at 0 and increments to 1."""
    st = _install_streamlit_stub(monkeypatch)
    cache_control = _import_fresh("cache_control")

    result = cache_control.bump()
    assert result == 1
    assert st.session_state["cache_buster"] == 1


def test_cache_control_bump_returns_zero_on_error(monkeypatch):
    """Bump returns 0 if an exception occurs."""
    # Create a session_state that raises on access
    class BadSessionState:
        def get(self, key, default=None):
            raise RuntimeError("Session error")

        def __setitem__(self, key, value):
            raise RuntimeError("Session error")

        def __getitem__(self, key):
            raise RuntimeError("Session error")

    st = types.SimpleNamespace()
    st.session_state = BadSessionState()
    monkeypatch.setitem(sys.modules, "streamlit", st)
    cache_control = _import_fresh("cache_control")

    result = cache_control.bump()
    assert result == 0


def test_cache_control_sequential_bumps(monkeypatch):
    """Multiple bumps increment sequentially."""
    st = _install_streamlit_stub(monkeypatch)
    cache_control = _import_fresh("cache_control")

    buster1 = cache_control.bump()
    buster2 = cache_control.bump()
    buster3 = cache_control.bump()

    assert buster1 == 1
    assert buster2 == 2
    assert buster3 == 3
