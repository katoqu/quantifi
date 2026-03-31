import streamlit as st
try:  # pragma: no cover - defensive for tests without full Streamlit
    import streamlit.components.v1 as components
except Exception:  # pragma: no cover
    components = None
import auth
from ui import pages
import utils


def _bridge_hash_params():
    if components is None:
        return
    components.html(
        """
<script>
(function() {
  const target = (window.parent && window.parent.location) ? window.parent : (window.top && window.top.location ? window.top : window);
  const hash = target.location.hash || "";
  if (!hash || hash.length < 2) return;
  const hashParams = new URLSearchParams(hash.slice(1));
  if (!hashParams.get("access_token")) return;
  const qs = new URLSearchParams(target.location.search);
  if (qs.get("access_token")) return; // already bridged
  hashParams.forEach((v, k) => qs.set(k, v));
  const newUrl = target.location.pathname + "?" + qs.toString();
  target.location.replace(newUrl);
})();
</script>
        """,
        height=0,
    )


def _force_auth_flow_from_params() -> bool:
    params = st.query_params
    token_type = str(params.get("type", "")).strip().lower()
    if token_type == "recovery":
        return True
    return "token_hash" in params or "code" in params or ("access_token" in params and "refresh_token" in params)

# 0. Ensure hash-based tokens are available as query params early
_bridge_hash_params()

# 1. Initialize State
auth.init_session_state()

# Inject CSS here so it is loaded once and never re-parsed during reruns
utils.apply_custom_tabs_css()
utils.apply_mobile_table_css()
utils.apply_landing_grid_css()

# 2. Authentication Check
if _force_auth_flow_from_params():
    auth.auth_page()
    st.stop()
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

# Optional admin page (allowlist approvals, etc.)
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
