import streamlit as st
from ui import manage_lookups, capture, visualize, metrics
import data_editor
import pandas as pd
import models
import utils
import auth
from datetime import timedelta

# 1. Initialize State
auth.init_session_state()
if "show_debug_panel" not in st.session_state:
    st.session_state.show_debug_panel = False

def show_debug_logs():
    # Only show if the user toggled it on
    if st.session_state.show_debug_panel:
        with st.expander("🛠 Auth Debug Logs (Newest First)", expanded=True):
            if not st.session_state.get("auth_debug"):
                st.info("No logs captured yet.")
            else:
                for log in reversed(st.session_state.auth_debug):
                    st.text(log)
                if st.button("Clear History"):
                    st.session_state.auth_debug = []
                    st.rerun()

# 2. Sidebar Toggle (Always visible)
#with st.sidebar:
#    st.title("Admin")
#    if st.button("Toggle Debug View"):
#        st.session_state.show_debug_panel = not st.session_state.show_debug_panel
#        st.rerun()

# 3. Execution Order
show_debug_logs() # Show logs at the very top if enabled

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

    # Show capture section
    capture.show_tracker_suite(selected_metric, unit_meta)

def settings_page():
    st.title("Settings")
    
    # Get data for selection
    cats = models.get_categories()
    units = models.get_units()
    
    # Manage lookups (categories and units)
    manage_lookups.show_manage_lookups()
    
    # Create metrics
    metrics.show_create_metric(cats, units)


def edit_data_page():
    st.title("Manage & Edit Data")
    
    metrics_list = models.get_metrics() or []
    if not metrics_list:
        st.info("No metrics defined yet.")
        return

    units = models.get_units() or []
    unit_meta = {u["id"]: u for u in units}

    metric_idx = st.selectbox(
        "Select metric to manage", 
        options=list(range(len(metrics_list))), 
        format_func=lambda i: utils.format_metric_label(metrics_list[i], unit_meta),
        key="edit_page_metric_select"
    )
    selected_metric = metrics_list[metric_idx]
    
    data_editor.show_data_management_suite(selected_metric, unit_meta)


# Update the Navigation
pg = st.navigation([
    st.Page(main_dashboard, title="Tracker", icon="📊"),
    st.Page(edit_data_page, title="Edit Data", icon="✏️"), # New Page
    st.Page(settings_page, title="Configure", icon="⚙️"),
])

pg.run()