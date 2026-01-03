import streamlit as st
import models
import utils
from ui import manage_lookups, capture, metrics, data_editor, importer, landing_page

import streamlit as st
import models
from utils import apply_custom_tabs_css 
from ui import landing_page, metrics, capture

def tracker_page():
    """
    Main dashboard controller. 
    Uses Session State as the single source of truth to avoid 'Duplicate Value' errors.
    """
    # 1. Fetch metrics from the database
    all_metrics = models.get_metrics() or []
    
    if not all_metrics:
        st.title("QuantifI")
        st.info("👋 Welcome! Go to Settings to create your first tracking target.")
        return

    # Apply the visual theme for the custom tabs
    apply_custom_tabs_css()

    # --- 1. STATE INITIALIZATION ---
    if "tracker_view_selector" not in st.session_state:
        st.session_state["tracker_view_selector"] = "Overview"

    # --- 2. HANDLE DEEP LINK TRIGGER (e.g., from Dashboard "➕" button) ---
    requested_mid = st.query_params.get("metric_id")
    if requested_mid:
        # Update session state to switch view and store the requested ID
        st.session_state["tracker_view_selector"] = "Record Data"
        st.session_state["requested_metric_id"] = requested_mid
        # Clear query params to prevent re-triggering on refresh
        st.query_params.clear()

    # --- 3. RENDER NAVIGATION (Segmented Radio Tabs) ---
    view_options = ["Overview", "Record Data"]
    st.radio(
        "Navigation", 
        view_options, 
        horizontal=True, 
        label_visibility="collapsed",
        key="tracker_view_selector" 
    )
    
    view_mode = st.session_state["tracker_view_selector"]
    st.divider()

    # --- 4. ROUTING LOGIC ---
    if view_mode == "Overview":
        # Clear the requested ID when returning to overview to reset selection later
        if "requested_metric_id" in st.session_state:
            del st.session_state["requested_metric_id"]
        landing_page.show_landing_page()
        
    else:
        # --- RECORD DATA VIEW ---
        active_mid = st.session_state.get("requested_metric_id")
        
        # FIX: Pass the 'active_mid' directly to the selector. 
        # This allows metrics.select_metric to find the correct index in its 
        # own internally sorted list, preventing the index-offset bug.
        selected_metric = metrics.select_metric(all_metrics, target_id=active_mid)
        
        if selected_metric:
            # Persist the selection in session state
            st.session_state["requested_metric_id"] = selected_metric['id']
            capture.show_tracker_suite(selected_metric)

def editor_page():
    """Dedicated page for historical data management and editing."""
    st.title("Edit Data")
    
    # 1. Fetch metrics
    metrics_list = models.get_metrics() or []
    if not metrics_list:
        st.info("No metrics found. Please create metrics in Settings before editing data.")
        return

    # 2. Initialize state for this specific page
    # This ensures the selection persists after a save/rerun
    if "editor_metric_id" not in st.session_state:
        st.session_state["editor_metric_id"] = None

    # 3. Call selector using the new target_id parameter
    active_id = st.session_state["editor_metric_id"]
    selected_metric = metrics.select_metric(metrics_list, target_id=active_id)
    
    if selected_metric:
        # 4. Update state with the user's current selection
        st.session_state["editor_metric_id"] = selected_metric['id']
        data_editor.show_data_management_suite(selected_metric)

def configure_page():
    """Refactored Settings page using Tabs for a cleaner UX."""
    st.title("Settings & Maintenance")
    
    cats = models.get_categories() or []
    metrics_list = models.get_metrics() or []
    last_ts = models.get_last_backup_timestamp()

    tab_metrics, tab_cats, tab_life = st.tabs([
        "📊 Manage Metrics", 
        "📁 Categories", 
        "💾 Data Lifecycle"
    ])

    with tab_metrics:
        if metrics_list:
            metrics.show_edit_metrics(metrics_list, cats)
            st.divider()
        metrics.show_create_metric(cats)

    with tab_cats:
        manage_lookups.show_manage_lookups()

    with tab_life:
        st.caption(f"🛡️ Last local backup: **{last_ts}**")
        importer.show_data_lifecycle_management()