import streamlit as st
from supabase import create_client, ClientOptions

_SB_CACHE_KEY = "supabase_client"
_SB_ADMIN_CACHE_KEY = "supabase_admin_client"

_sb_fallback = None
_sb_admin_fallback = None

def _can_use_session_state() -> bool:
    try:
        _ = st.session_state
        return True
    except Exception:
        return False

def get_supabase():
    """
    Initializes and caches the Supabase client in session state 
    to prevent logout on every rerun.
    """
    global _sb_fallback

    if _can_use_session_state():
        if _SB_CACHE_KEY not in st.session_state:
            options = ClientOptions(
                auto_refresh_token=True,
                persist_session=True,
                flow_type="pkce",
            )
            st.session_state[_SB_CACHE_KEY] = create_client(
                st.secrets["SUPABASE_URL"],
                st.secrets["SUPABASE_KEY"],
                options=options,
            )
        return st.session_state[_SB_CACHE_KEY]

    if _sb_fallback is None:
        options = ClientOptions(
            auto_refresh_token=True,
            persist_session=True,
            flow_type="pkce",
        )
        _sb_fallback = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_KEY"],
            options=options,
        )
    return _sb_fallback

def get_supabase_admin():
    global _sb_admin_fallback

    if _can_use_session_state():
        if _SB_ADMIN_CACHE_KEY not in st.session_state:
            st.session_state[_SB_ADMIN_CACHE_KEY] = create_client(
                st.secrets["SUPABASE_URL"],
                st.secrets["SUPABASE_SERVICE_ROLE_KEY"],
            )
        return st.session_state[_SB_ADMIN_CACHE_KEY]

    if _sb_admin_fallback is None:
        _sb_admin_fallback = create_client(
            st.secrets["SUPABASE_URL"],
            st.secrets["SUPABASE_SERVICE_ROLE_KEY"],
        )
    return _sb_admin_fallback

class _LazyClient:
    def __init__(self, factory, label: str):
        self._factory = factory
        self._label = label

    def _get(self):
        return self._factory()

    def __getattr__(self, name: str):
        return getattr(self._get(), name)

    def __repr__(self) -> str:
        return f"<LazySupabaseClient {self._label}>"

# Lazy proxies: safe to import without Streamlit secrets configured.
sb = _LazyClient(get_supabase, "sb")
sb_admin = _LazyClient(get_supabase_admin, "sb_admin")
