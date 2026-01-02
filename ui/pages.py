import streamlit as st
import models
import utils
from ui import manage_lookups, capture, metrics, data_editor, importer, landing_page

def tracker_page():
    """Main dashboard logic with a startup overview and pre-fill logic."""
    all_metrics = models.get_metrics() or []
    
    if not all_metrics:
        st.title("QuantifI")
        st.info("👋 Welcome! Go to Settings to create your first metric.")
        return

    # 1. Initialize view_mode in session state if not present
    if "view_mode" not in st.session_state:
        st.session_state["view_mode"] = "Overview"

    # 2. Check for incoming metric_id from the landing page 'Record' link
    requested_mid = st.query_params.get("metric_id")

    # 3. View Switcher (Radio)
    # If we have a requested_mid, we force the view to 'Record Data'
    default_view_idx = 1 if requested_mid else (0 if st.session_state["view_mode"] == "Overview" else 1)

    view_mode = st.radio(
        "View", ["Overview", "Record Data"], 
        index=default_view_idx,
        horizontal=True, 
        label_visibility="collapsed",
        key="view_mode_selector"
    )
    
    # Sync manual radio changes back to session state
    st.session_state["view_mode"] = view_mode

    if view_mode == "Overview":
        # Clear query params when returning to overview so the next visit is clean
        st.query_params.clear()
        landing_page.show_landing_page()
    else:
        # --- Detailed Tracker View ---
        st.title("Record Metric")
        
        # Determine which metric should be selected by default
        default_idx = 0
        if requested_mid:
            for idx, m in enumerate(all_metrics):
                if m['id'] == requested_mid:
                    default_idx = idx
                    break

        # Pass the calculated index to the selector
        selected_metric = metrics.select_metric(all_metrics, index=default_idx)
        
        if selected_metric:
            capture.show_tracker_suite(selected_metric)


def editor_page():
    """Dedicated page for historical data management and editing."""
    st.title("Manage & Edit Data")
    
    metrics_list = models.get_metrics() or []
    if not metrics_list:
        st.info("No metrics found. Please create metrics in Settings before editing data.")
        return

    selected_metric = metrics.select_metric(metrics_list)
    
    if selected_metric:
        data_editor.show_data_management_suite(selected_metric)


def configure_page():
    """Refactored Settings page using Tabs for a cleaner UX."""
    st.title("Settings & Maintenance")
    
    # Refresh data each time the settings page is loaded
    cats = models.get_categories() or []
    metrics_list = models.get_metrics() or []
    last_ts = models.get_last_backup_timestamp()

    tab_metrics, tab_cats, tab_life = st.tabs([
        "📊 Manage Metrics", 
        "📁 Categories", 
        "💾 Data Lifecycle"
    ])

    with tab_metrics:
        # Show existing metrics first for management, followed by creation
        if metrics_list:
            metrics.show_edit_metrics(metrics_list, cats)
            st.divider()
        metrics.show_create_metric(cats)

    with tab_cats:
        manage_lookups.show_manage_lookups()

    with tab_life:
        st.caption(f"🛡️ Last local backup: **{last_ts}**")
        importer.show_data_lifecycle_management()