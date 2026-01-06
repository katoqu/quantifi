import streamlit as st
import models
import utils
from ui import manage_lookups, capture, metrics, data_editor, importer, landing_page

def tracker_page():
    """
    Main dashboard controller optimized for mobile. 
    Uses Session State as the single source of truth for 'Sticky' selection.
    """
    # Fix: Ensure the tab selector doesn't hold an invalid value
    valid_tabs = ["Overview", "Record", "Analytics", "Edit"]
    if st.session_state.get("tracker_view_selector") not in valid_tabs:
        st.session_state["tracker_view_selector"] = "Overview"

    # 1. ALWAYS FETCH METRICS (Lightweight)
    all_metrics = models.get_metrics()
    
    if all_metrics is None:
        st.spinner("Syncing metrics...")
        st.stop()
        
    # 3. EMPTY STATE: Only show if we explicitly got an empty list []
    if not all_metrics:
        st.title("QuantifI")
        st.info("👋 Welcome! Go to Settings to create your first tracking target.")
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
    
    # Use segmented_control for a high-quality mobile tab feel
    st.segmented_control(
        "Navigation", 
        options=view_options, 
        selection_mode="single",
        label_visibility="collapsed",
        key="tracker_view_selector" 
    )
    
    view_mode = st.session_state["tracker_view_selector"]

    # 2. SELECTOR-AT-TOP CHANGE:
    # If we are not on the 'Overview' page, show the metric selector immediately.
    selected_metric = None
    if view_mode != "Overview":
        active_id = st.session_state.get("last_active_mid")
        # Call the selector here so it appears at the top
        selected_metric = metrics.select_metric(all_metrics, target_id=active_id)
        
        if selected_metric:
            st.session_state["last_active_mid"] = selected_metric['id']

    st.divider()

    # 4. ROUTING LOGIC (Simplified)
    if view_mode == "Overview":
        all_entries = models.get_all_entries_bulk()
        landing_page.show_landing_page(all_metrics, all_entries) #
        
    elif view_mode == "Record" and selected_metric:
        # No longer need to call metrics.select_metric here
        capture.show_tracker_suite(selected_metric)

    elif view_mode == "Analytics" and selected_metric:
        # No longer need to call metrics.select_metric here
        landing_page.show_advanced_analytics_view(selected_metric)

    elif view_mode == "Edit" and selected_metric:
        # No longer need to call metrics.select_metric here
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
    """
    Refactored Settings: Uses segmented control for a 'sticky' state
    that survives script reruns during imports.
    """
    st.title("Settings & Maintenance")
    
    # 1. Initialize session state for the tab if it doesn't exist
    if "config_tab_selection" not in st.session_state:
        st.session_state["config_tab_selection"] = "📊 Edit Metric"

    cats = models.get_categories() or []
    metrics_list = models.get_metrics() or []
    last_ts = models.get_last_backup_timestamp()

    # 2. Use segmented_control instead of st.tabs for persistence
    tab_options = [
        "📊 Edit Metric", 
        "✨ New Metric",
        "📁 Categories", 
        "⚙️ Export & Import"
    ]
    
    selected_tab = st.segmented_control(
        "Settings Menu",
        options=tab_options,
        selection_mode="single",
        label_visibility="collapsed",
        key="config_tab_selection" # This makes it 'sticky'
    )
    
    st.divider()

    # 3. Content Routing based on selection
    if selected_tab == "📊 Edit Metric":
        if metrics_list:
            metrics.show_edit_metrics(metrics_list, cats)
        else:
            st.info("No metrics found yet.")

    elif selected_tab == "✨ New Metric":
        metrics.show_create_metric(cats)

    elif selected_tab == "📁 Categories":
        manage_lookups.show_manage_lookups()

    elif selected_tab == "⚙️ Export & Import":
        st.caption(f"🛡️ Last local backup: **{last_ts}**")
        importer.show_data_lifecycle_management()