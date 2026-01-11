import streamlit as st
import models
import utils
from ui import manage_lookups, capture, metrics, data_editor, importer, landing_page

def tracker_page():
    """
    Main dashboard controller optimized for mobile. 
    Uses Session State as the single source of truth for 'Sticky' selection.
    """
    if st.session_state.get("nav_to_record_trigger"):
        st.session_state["tracker_view_selector"] = "Record"
        st.session_state["nav_to_record_trigger"] = False # Reset trigger

    # Fix: Ensure the tab selector doesn't hold an invalid value
    valid_tabs = ["Overview", "Record", "Analytics", "Edit"]
    if st.session_state.get("tracker_view_selector") not in valid_tabs:
        st.session_state["tracker_view_selector"] = "Overview"

    # 1. ALWAYS FETCH METRICS (Lightweight)
    all_metrics = models.get_metrics(include_archived=False)
    
    if all_metrics is None:
        st.spinner("Syncing metrics...")
        st.stop()
        
    # 3. EMPTY STATE: Only show if we explicitly got an empty list []
    if not all_metrics:
        st.title("QuantifI")
        st.info("No active metrics. Restore archived metrics in Settings or create a new one.")
        return

    # 2. Apply the visual theme for the custom tabs (from utils.py)
    utils.apply_custom_tabs_css()

    # --- 3. STATE INITIALIZATION ---
    if "tracker_view_selector" not in st.session_state:
        st.session_state["tracker_view_selector"] = "Overview"
    if "metric_search" not in st.session_state:
        st.session_state["metric_search"] = ""
    if "last_active_mid" not in st.session_state:
        st.session_state["last_active_mid"] = None
    if "use_time_sticky" not in st.session_state:
        st.session_state["use_time_sticky"] = False
    if "active_cat_filter" not in st.session_state:
        st.session_state["active_cat_filter"] = "All"

    # --- 4. HANDLE DEEP LINK TRIGGER (e.g., from Dashboard "➕" button) ---
    requested_mid = st.query_params.get("metric_id")
    if requested_mid:
        # Switch view to recording mode
        st.session_state["tracker_view_selector"] = "Record"
        # Set this as the sticky active metric
        st.session_state["last_active_mid"] = requested_mid
        # Clear query params to prevent re-triggering on browser refresh
        st.query_params.clear()


    # --- 5. RENDER NAVIGATION (Modern Segmented Tabs) ---
    view_options = ["Overview", "Record", "Analytics", "Edit"]
    
    # WRAP IN CONTAINER FOR STICKY CSS TO TARGET
    with st.container():
        st.segmented_control(
            "Navigation", 
            options=view_options, 
            selection_mode="single",
            label_visibility="collapsed",
            key="tracker_view_selector" 
        )
        
        view_mode = st.session_state["tracker_view_selector"]
        selected_metric = None

        # NEW: Show Back Button on all sub-views except Overview
        if view_mode != "Overview":
            utils.render_back_button(
                target_page_title="Tracker", 
                target_tab="Overview", 
                breadcrumb=view_mode
            )
#        st.divider()    

    # 4. ROUTING LOGIC (Simplified)
    if view_mode != "Overview":
        active_id = st.session_state.get("last_active_mid")
        selected_metric = metrics.select_metric(all_metrics, target_id=active_id)
        
        if selected_metric:
            # Update the sticky ID so it stays focused across tabs
            st.session_state["last_active_mid"] = selected_metric['id']

    # --- 4. ROUTING LOGIC ---
    if view_mode == "Overview":
        all_entries = models.get_all_entries_bulk()
        landing_page.show_landing_page(all_metrics, all_entries)
        
    elif view_mode == "Record" and selected_metric:
        capture.show_tracker_suite(selected_metric)

    elif view_mode == "Analytics" and selected_metric:
        landing_page.show_advanced_analytics_view(selected_metric)

    elif view_mode == "Edit" and selected_metric:
        data_editor.show_data_management_suite(selected_metric)
        
def editor_page():
    """Dedicated page for historical data management and editing."""
    st.title("Edit")
    
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
    """Refactored Settings with Sticky Header and Breadcrumbs."""
    st.title("Settings & Maintenance")
    
    # 1. Initialize session state
    if "config_tab_selection" not in st.session_state:
        st.session_state["config_tab_selection"] = "📊 Edit Metric"

    # 2. STICKY HEADER CONTAINER
    # Wrapping everything in one container allows the CSS to pin it as a single block
    with st.container():
        tab_options = ["📊 Edit Metric", "✨ New Metric", "📁 Categories", "⚙️ Export & Import"]
        
        selected_tab = st.segmented_control(
            "Settings Menu",
            options=tab_options,
            selection_mode="single",
            label_visibility="collapsed",
            key="config_tab_selection"
        )
        
        # Determine breadcrumb text (e.g., 'Edit Metric' from '📊 Edit Metric')
        bc_text = selected_tab.split(" ", 1)[-1] if selected_tab else "Settings"
        
        utils.render_back_button(
            target_page_title="Tracker", 
            target_tab="Overview", 
            breadcrumb=bc_text
        )
        #st.divider()

    # 3. Data Loading & Content Routing
    cats = models.get_categories() or []
    metrics_list = models.get_metrics(include_archived=True) or []
    
    if selected_tab == "📊 Edit Metric":    
        metrics.show_edit_metrics(metrics_list, cats)
    elif selected_tab == "✨ New Metric":
        metrics.show_create_metric(cats)
    elif selected_tab == "📁 Categories":
        manage_lookups.show_manage_lookups()
    elif selected_tab == "⚙️ Export & Import":
        last_ts = models.get_last_backup_timestamp()
        st.caption(f"🛡️ Last local backup: **{last_ts}**")
        importer.show_data_lifecycle_management()