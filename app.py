import streamlit as st
from ui import manage_lookups, capture, visualize, metrics
import models
import utils
import auth

# 1. Initialize authentication
auth.init_session_state()

# 2. DEBUG VIEWER (Add this at the top)
if "auth_debug" in st.session_state and st.session_state.auth_debug:
    with st.expander("🛠 Auth Debug Logs", expanded=True):
        for log in st.session_state.auth_debug:
            st.text(log)
        if st.button("Clear Logs"):
            st.session_state.auth_debug = []
            st.rerun()

# 3. If not authenticated, show auth page
if not auth.is_authenticated():
    auth.auth_page()
    st.stop()

# 4. Sidebar Logout Logic
# This stays visible on both "Tracker" and "Configure" pages
with st.sidebar:
    st.write(f"Logged in as: **{auth.get_current_user().email}**")
    if st.button("Log Out", use_container_width=True):
        auth.sign_out()
        st.rerun()

def main_dashboard():
    st.title("QuantifI - Dashboard")

    # select metric and capture data
    metrics = models.get_metrics() or []
    if not metrics:
        st.info("No metrics defined yet. Create one in 'Define & configure'.")
        return

    units = models.get_units() or []
    unit_meta = {u["id"]: u for u in units}

    metric_idx = st.selectbox("Metric to capture", options=list(range(len(metrics))), format_func=lambda i: utils.format_metric_label(metrics[i], unit_meta))
    selected_metric = metrics[metric_idx]

    dfe, m_unit, m_name = utils.collect_data(selected_metric, unit_meta)

    # Show capture section
    capture.show_capture(selected_metric, unit_meta)

    # Show collapsible editable data table
    if dfe is not None:
        with st.expander("View Editable Metric Table", expanded=False):
            editable_df = visualize.editable_metric_table(dfe, m_unit, selected_metric.get("id"))

    # Collect data for visualization and show plot
    visualize.show_visualizations(dfe, m_unit, m_name )

def settings_page():
    st.title("Settings")
    
    # Get data for selection
    cats = models.get_categories()
    units = models.get_units()
    
    # Manage lookups (categories and units)
    manage_lookups.show_manage_lookups()
    
    # Create metrics
    metrics.show_create_metric(cats, units)

# Define pages with icons
pg = st.navigation([
    st.Page(main_dashboard, title="Tracker", icon="📊"),
    st.Page(settings_page, title="Configure", icon="⚙️"),
])

pg.run()
