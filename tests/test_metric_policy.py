import pytest
import sys
import types
import importlib


def _install_streamlit_stub(monkeypatch, session_state=None):
    """Install a minimal streamlit stub to allow module imports."""
    st = types.SimpleNamespace()
    st.session_state = session_state if session_state is not None else {}
    monkeypatch.setitem(sys.modules, "streamlit", st)
    return st


def _import_fresh(name: str):
    """Import a module fresh, reloading it."""
    sys.modules.pop(name, None)
    return importlib.import_module(name)


def test_metric_policy_default_policy_has_ignore_missing():
    """Default policy uses 'ignore_missing' for missing_policy."""
    from metric_policy import DEFAULT_POLICY

    assert DEFAULT_POLICY.missing_policy == "ignore_missing"
    assert DEFAULT_POLICY.daily_agg == "sum"


def test_metric_policy_metric_key_uses_id_if_provided():
    """Metric key prefers metric_id over metric_name."""
    from metric_policy import _metric_key

    assert _metric_key(metric_name="Sleep", metric_id="uuid-123") == "uuid-123"
    assert _metric_key(metric_name="Sleep", metric_id=None) == "sleep"


def test_metric_policy_metric_key_normalizes_name(monkeypatch):
    """Metric key normalizes name to lowercase stripped."""
    from metric_policy import _metric_key

    assert _metric_key(metric_name="  Sleep Quality  ", metric_id=None) == "sleep quality"
    assert _metric_key(metric_name="YOGA", metric_id=None) == "yoga"
    assert _metric_key(metric_name="", metric_id=None) == ""


def test_metric_policy_get_session_state_returns_none_without_streamlit(
    monkeypatch,
):
    """_try_get_session_state returns None if streamlit import fails."""
    monkeypatch.setitem(sys.modules, "streamlit", None)
    metric_policy = _import_fresh("metric_policy")

    result = metric_policy._try_get_session_state()
    assert result is None


def test_metric_policy_get_session_state_returns_state_dict(monkeypatch):
    """_try_get_session_state returns the streamlit session_state dict."""
    st = _install_streamlit_stub(monkeypatch, session_state={"key": "value"})
    metric_policy = _import_fresh("metric_policy")

    result = metric_policy._try_get_session_state()
    assert result == {"key": "value"}


def test_metric_policy_set_missing_is_zero_override_with_metric_id(monkeypatch):
    """Setting override with metric_id stores in session state."""
    st = _install_streamlit_stub(monkeypatch)
    metric_policy = _import_fresh("metric_policy")

    metric_policy.set_missing_is_zero_override(metric_id="uuid-123", enabled=True)
    assert st.session_state.get("metric_missing_is_zero::uuid-123") is True

    metric_policy.set_missing_is_zero_override(metric_id="uuid-123", enabled=False)
    assert st.session_state.get("metric_missing_is_zero::uuid-123") is False


def test_metric_policy_set_missing_is_zero_override_with_metric_name(monkeypatch):
    """Setting override with metric_name normalizes and stores."""
    st = _install_streamlit_stub(monkeypatch)
    metric_policy = _import_fresh("metric_policy")

    metric_policy.set_missing_is_zero_override(metric_name="  Sleep Quality  ", enabled=True)
    assert st.session_state.get("metric_missing_is_zero::sleep quality") is True


def test_metric_policy_set_missing_is_zero_override_requires_key(monkeypatch):
    """Setting override with empty key does nothing."""
    st = _install_streamlit_stub(monkeypatch)
    metric_policy = _import_fresh("metric_policy")

    metric_policy.set_missing_is_zero_override(metric_name="", metric_id=None, enabled=True)
    assert len(st.session_state) == 0


def test_metric_policy_get_missing_is_zero_override_returns_none_if_not_set(
    monkeypatch,
):
    """Getting override returns None if not previously set."""
    st = _install_streamlit_stub(monkeypatch)
    metric_policy = _import_fresh("metric_policy")

    result = metric_policy.get_missing_is_zero_override(metric_id="uuid-456")
    assert result is None


def test_metric_policy_get_missing_is_zero_override_returns_stored_value(monkeypatch):
    """Getting override returns the stored boolean value."""
    st = _install_streamlit_stub(monkeypatch)
    st.session_state["metric_missing_is_zero::uuid-123"] = True
    metric_policy = _import_fresh("metric_policy")

    result = metric_policy.get_missing_is_zero_override(metric_id="uuid-123")
    assert result is True


def test_metric_policy_resolve_metric_policy_uses_default(monkeypatch):
    """Resolving policy without override returns default policy."""
    st = _install_streamlit_stub(monkeypatch)
    metric_policy = _import_fresh("metric_policy")

    policy = metric_policy.resolve_metric_policy(metric_name="Sleep")
    assert policy.missing_policy == "ignore_missing"
    assert policy.daily_agg == "sum"


def test_metric_policy_resolve_metric_policy_applies_override_true(monkeypatch):
    """Resolving policy with override=True changes to missing_is_zero."""
    st = _install_streamlit_stub(monkeypatch)
    st.session_state["metric_missing_is_zero::sleep"] = True
    metric_policy = _import_fresh("metric_policy")

    policy = metric_policy.resolve_metric_policy(metric_name="sleep")
    assert policy.missing_policy == "missing_is_zero"
    assert policy.daily_agg == "sum"


def test_metric_policy_resolve_metric_policy_applies_override_false(monkeypatch):
    """Resolving policy with override=False keeps ignore_missing."""
    st = _install_streamlit_stub(monkeypatch)
    st.session_state["metric_missing_is_zero::sleep"] = False
    metric_policy = _import_fresh("metric_policy")

    policy = metric_policy.resolve_metric_policy(metric_name="sleep")
    assert policy.missing_policy == "ignore_missing"
    assert policy.daily_agg == "sum"


def test_metric_policy_resolve_metric_policy_preserves_daily_agg_on_override(
    monkeypatch,
):
    """Resolving policy preserves daily_agg when applying override."""
    st = _install_streamlit_stub(monkeypatch)
    st.session_state["metric_missing_is_zero::sleep"] = True
    metric_policy = _import_fresh("metric_policy")

    policy = metric_policy.resolve_metric_policy(metric_name="sleep")
    # Should preserve the daily_agg from default or POLICY_BY_METRIC_NAME
    assert policy.daily_agg == "sum"
