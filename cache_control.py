import streamlit as st


_BUSTER_KEY = "cache_buster"


def get_buster() -> int:
    try:
        return int(st.session_state.get(_BUSTER_KEY, 0))
    except Exception:
        return 0


def bump() -> int:
    """
    Invalidates per-session cached reads by incrementing `st.session_state.cache_buster`.

    This is intentionally lighter than `st.cache_data.clear()` (which is global and can
    cause cross-user churn in multi-user deployments).
    """
    try:
        st.session_state[_BUSTER_KEY] = get_buster() + 1
        return int(st.session_state[_BUSTER_KEY])
    except Exception:
        return 0

