import streamlit as st
from supabase import create_client, ClientOptions

def get_supabase():
    """
    Initializes and caches the Supabase client in session state 
    to prevent logout on every rerun.
    """
    if "supabase_client" not in st.session_state:
        # 1. Update options to allow persistence
        options = ClientOptions(
            auto_refresh_token=True,
            persist_session=True,  # Change this to True
            flow_type="pkce"
        )
        
        # 2. Initialize and store in session_state
        st.session_state.supabase_client = create_client(
            st.secrets["SUPABASE_URL"], 
            st.secrets["SUPABASE_KEY"],
            options=options
        )
    
    return st.session_state.supabase_client

# Replace the global 'sb' variable with the function-based one
sb = get_supabase()

# Admin client usually doesn't need persistence as it uses a Service Role Key
sb_admin = create_client(
    st.secrets["SUPABASE_URL"], 
    st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
)