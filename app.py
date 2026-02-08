import streamlit as st
import auth
from ui import pages
import utils

# 1. Initialize State
auth.init_session_state()

# Inject CSS here so it is loaded once and never re-parsed during reruns
utils.apply_custom_tabs_css()
utils.apply_mobile_table_css()
utils.apply_landing_grid_css()

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

# Optional admin page (invite users, etc.)
if auth.is_admin():
    my_pages.append(st.Page(pages.admin_page, title="Admin", icon="🛡️"))

# Store them in session state so they can be accessed anywhere
st.session_state["nav_pages"] = my_pages

# Pass the list to navigation
pg = st.navigation(my_pages)

# 5. Execution
try:
    pg.run()
except Exception as e:
    st.error(f"An unexpected error occurred: {e}")
