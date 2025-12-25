import streamlit as st
from supabase import create_client, ClientOptions

# Initialize the client once
# Options ensure the session persists across page reruns
sb = create_client(
    st.secrets["SUPABASE_URL"], 
    st.secrets["SUPABASE_KEY"],
    options=ClientOptions(
        auto_refresh_token=True,
        persist_session=True
    )
)

sb_admin = create_client(
    st.secrets["SUPABASE_URL"], 
    st.secrets["SUPABASE_SERVICE_ROLE_KEY"],
    options=ClientOptions(
        auto_refresh_token=True,
        persist_session=True
    )
)