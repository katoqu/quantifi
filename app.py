import streamlit as st
import auth
from ui import pages

# 1. Initialize State
auth.init_session_state()

# 2. Authentication Check
if not auth.is_authenticated():
    auth.auth_page()
    st.stop()

# 3. Sidebar Profile & Logout
with st.sidebar:
    st.write(f"Logged in as: **{auth.get_current_user().email}**")
    st.divider() # Visual separation for the logout button
    if st.button("Log Out", use_container_width=True, type="secondary"):
        auth.sign_out()

# 4. Navigation Definition
# Define your pages as a list
my_pages = [
    st.Page(pages.tracker_page, title="Tracker", icon="📊", default=True),
    st.Page(pages.configure_page, title="Configure", icon="⚙️"),
]

# Store them in session state so they can be accessed anywhere
st.session_state["nav_pages"] = my_pages

# Pass the list to navigation
pg = st.navigation(my_pages)

# 5. Execution
try:
    pg.run()
except Exception as e:
    st.error(f"An unexpected error occurred: {e}")