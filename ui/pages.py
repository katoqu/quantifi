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
    Main dashboard controller optimized for mobile. 
    Uses Session State as the single source of truth for 'Sticky' selection.
    """
    # 1. Fetch metrics from the database
    all_metrics = models.get_metrics() or []
    
    if not all_metrics:
        st.title("QuantifI")
        st.info("👋 Welcome! Go to Settings to create your first tracking target.")
        return

    # 2. Apply the visual theme for the custom tabs (from utils.py)
    utils.apply_custom_tabs_css()

    # --- 3. STATE INITIALIZATION ---
    if "tracker_view_selector" not in st.session_state:
        st.session_state["tracker_view_selector"] = "Overview"
    
    # Initialize the sticky metric ID if it doesn't exist
    if "last_active_mid" not in st.session_state:
        st.session_state["last_active_mid"] = None

    # ADD THIS: Initialize category filter here
    if "active_cat_filter" not in st.session_state:
        st.session_state["active_cat_filter"] = "All"

    # --- 4. HANDLE DEEP LINK TRIGGER (e.g., from Dashboard "➕" button) ---
    requested_mid = st.query_params.get("metric_id")
    if requested_mid:
        # Switch view to recording mode
        st.session_state["tracker_view_selector"] = "Record Data"
        # Set this as the sticky active metric
        st.session_state["last_active_mid"] = requested_mid
        # Clear query params to prevent re-triggering on browser refresh
        st.query_params.clear()


# --- 5. RENDER NAVIGATION (Modern Segmented Tabs) ---
    view_options = ["Overview", "Record Data"]
    
    # Use segmented_control for a high-quality mobile tab feel
    st.segmented_control(
        "Navigation", 
        options=view_options, 
        selection_mode="single",
        label_visibility="collapsed",
        key="tracker_view_selector" 
    )
    
    view_mode = st.session_state["tracker_view_selector"]
    st.divider()

    # --- 6. ROUTING LOGIC ---
    if view_mode == "Overview":
        landing_page.show_landing_page()
        
    else:
        # --- RECORD DATA VIEW ---
        # Get the ID from the sticky session state
        active_id = st.session_state.get("last_active_mid")
        
        # Pass the sticky ID to the selector to auto-focus the right metric
        selected_metric = metrics.select_metric(all_metrics, target_id=active_id)
        
        if selected_metric:
            # Update the sticky state if the user manually changes selection in the dropdown
            st.session_state["last_active_mid"] = selected_metric['id']
            # Show the capture suite (Capture + Visualization)
            capture.show_tracker_suite(selected_metric)

def editor_page():
    """Dedicated page for historical data management and editing."""
    st.title("Edit Data")
    
    # 1. Fetch metrics
    metrics_list = models.get_metrics() or []
    if not metrics_list:
        st.info("No metrics found. Please create metrics in Settings before editing data.")
        return

    # 2. SMART DEFAULT: Link to the shared global active metric key
    if "last_active_mid" not in st.session_state:
        st.session_state["last_active_mid"] = None

    # 3. Use the shared 'sticky' ID
    active_id = st.session_state["last_active_mid"]
    selected_metric = metrics.select_metric(metrics_list, target_id=active_id)
    
    if selected_metric:
        # 4. Update the shared state so it sticks if changed here too
        st.session_state["last_active_mid"] = selected_metric['id']
        data_editor.show_data_management_suite(selected_metric)

def configure_page():
    """
    Refactored Settings: Distinguishes between Metric management 
    and Category organization using a task-oriented tab structure.
    """
    st.title("Settings & Maintenance")
    
    cats = models.get_categories() or []
    metrics_list = models.get_metrics() or []
    last_ts = models.get_last_backup_timestamp()

    # Semantic separation: Metrics vs Categories vs System
    tab_metrics, tab_new_metric, tab_cats, tab_system = st.tabs([
        "📊 Edit Metric", 
        "✨ New Metric",
        "📁 Categories", 
        "⚙️ Export & Import"
    ])

    with tab_metrics:
        # Focus: Modifying existing tracking targets
        if metrics_list:
            metrics.show_edit_metrics(metrics_list, cats)
        else:
            st.info("No metrics found yet.")

    with tab_new_metric:
        # Focus: Pure creation flow (clears the screen of existing data)
        metrics.show_create_metric(cats)

    with tab_cats:
        # Focus: Organizational groups (Mirrors your current compact logic)
        manage_lookups.show_manage_lookups()

    with tab_system:
        # Focus: Backend and data lifecycle
        st.caption(f"🛡️ Last local backup: **{last_ts}**")
        importer.show_data_lifecycle_management()