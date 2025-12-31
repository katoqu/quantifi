import streamlit as st
import auth
from ui import pages

# 1. Initialize State
auth.init_session_state()

# 2. Authentication Check
if not auth.is_authenticated():
    auth.auth_page()
    st.stop()

# 3. Sidebar Logout Logic
with st.sidebar:
    st.write(f"Logged in as: **{auth.get_current_user().email}**")
    if st.button("Log Out", use_container_width=True):
        auth.sign_out()

# 4. Navigation Definition using the new pages module
pg = st.navigation([
    st.Page(pages.tracker_page, title="Tracker", icon="📊"),
    st.Page(pages.editor_page, title="Edit Data", icon="✏️"),
    st.Page(pages.configure_page, title="Configure", icon="⚙️"),
])

pg.run()