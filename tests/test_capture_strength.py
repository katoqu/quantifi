import importlib

import pytest

pytest.importorskip("streamlit")


capture = importlib.import_module("ui.capture")


def test_is_strength_metric_detects_strength_session_kind():
    assert capture._is_strength_metric({"metric_kind": "strength_session"}) is True


def test_is_strength_metric_returns_false_for_standard_metrics():
    assert capture._is_strength_metric({"metric_kind": "quantitative"}) is False
    assert capture._is_strength_metric({}) is False


def test_format_success_value_uses_strength_summary_when_present():
    payload = {"summary": "80.0 kg × 5 reps × 3 sets"}
    assert capture._format_success_value(payload, None, "kg") == "80.0 kg × 5 reps × 3 sets"


def test_format_success_value_falls_back_to_numeric_value():
    assert capture._format_success_value(None, 72.5, "kg") == "72.5 kg"


def test_render_strength_workout_form_initializes_empty_state():
    import streamlit as st

    # Mock session_state
    class MockSessionState:
        _data = {}
        
        @classmethod
        def __contains__(cls, key):
            return key in cls._data
        
        @classmethod
        def __getitem__(cls, key):
            return cls._data[key]
        
        @classmethod
        def __setitem__(cls, key, value):
            cls._data[key] = value
        
        @classmethod
        def get(cls, key, default=None):
            return cls._data.get(key, default)

    st.session_state = MockSessionState()
    
    result = capture._render_strength_workout_form("test_metric", "kg")
    
    # Should return None when no sets are added
    assert result is None
    
    # State should be initialized
    assert "strength_sets_state_test_metric" in st.session_state
    assert st.session_state["strength_sets_state_test_metric"] == []


def test_render_strength_workout_form_adds_and_returns_sets():
    import streamlit as st

    # Mock session_state
    class MockSessionState:
        _data = {}
        
        @classmethod
        def __contains__(cls, key):
            return key in cls._data
        
        @classmethod
        def __getitem__(cls, key):
            return cls._data[key]
        
        @classmethod
        def __setitem__(cls, key, value):
            cls._data[key] = value
        
        @classmethod
        def get(cls, key, default=None):
            return cls._data.get(key, default)

    st.session_state = MockSessionState()
    
    # First call initializes state
    result = capture._render_strength_workout_form("test_metric", "kg")
    assert result is None
    
    # Simulate adding sets through session state (as the UI would)
    state_key = "strength_sets_state_test_metric"
    st.session_state[state_key] = [
        {"load_kg": 80.0, "reps": 5},
        {"load_kg": 82.5, "reps": 3}
    ]
    
    # Call again to get the result
    result = capture._render_strength_workout_form("test_metric", "kg")
    
    # Should return the correct summary and sets
    assert result is not None
    assert result["summary"] == "80.0 kg × 5/3 reps × 2 sets"
    assert len(result["sets"]) == 2
    assert result["sets"][0]["load_kg"] == 80.0
    assert result["sets"][0]["reps"] == 5
    assert result["sets"][1]["load_kg"] == 82.5
    assert result["sets"][1]["reps"] == 3
    assert result["load_kg"] == 80.0


def test_render_strength_workout_form_persists_data_across_calls():
    import streamlit as st

    # Mock session_state
    class MockSessionState:
        _data = {}
        
        @classmethod
        def __contains__(cls, key):
            return key in cls._data
        
        @classmethod
        def __getitem__(cls, key):
            return cls._data[key]
        
        @classmethod
        def __setitem__(cls, key, value):
            cls._data[key] = value
        
        @classmethod
        def get(cls, key, default=None):
            return cls._data.get(key, default)

    st.session_state = MockSessionState()
    
    # First call
    capture._render_strength_workout_form("persist_test", "kg")
    state_key = "strength_sets_state_persist_test"
    
    # Verify state is initialized
    assert state_key in st.session_state
    assert st.session_state[state_key] == []
    
    # Add a set
    st.session_state[state_key].append({"load_kg": 60.0, "reps": 8})
    
    # Second call should still have the set
    result = capture._render_strength_workout_form("persist_test", "kg")
    assert result is not None
    assert len(result["sets"]) == 1
    assert result["sets"][0]["load_kg"] == 60.0
    assert result["sets"][0]["reps"] == 8
