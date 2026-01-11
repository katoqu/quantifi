import streamlit as st
import models
import utils
from ui import manage_lookups, capture, metrics, data_editor, importer, landing_page

def tracker_page():
    """
    Main dashboard controller optimized for mobile. 
    Uses 'Pre-render Logic' to handle back-navigation safely with st.pills.
    """
    # --- 1. PRE-RENDER NAVIGATION LOGIC (CRITICAL FIX) ---
    # We check if the back-pill was clicked before any other widgets are rendered.
    # This prevents the 'modification after instantiation' error.
    back_pill_key = "pnav_Tracker_Overview"
    if st.session_state.get(back_pill_key) is not None:
        # Reset the pill state so it doesn't trigger on every rerun
        st.session_state[back_pill_key] = None
        # Safely update the shared state for the segmented control
        st.session_state["tracker_view_selector"] = "Overview"

    # Handle deep link triggers from other parts of the app
    if st.session_state.get("nav_to_record_trigger"):
        st.session_state["tracker_view_selector"] = "Record"
        st.session_state["nav_to_record_trigger"] = False 

    # --- 2. DATA LOADING ---
    all_metrics = models.get_metrics(include_archived=False)
    
    if all_metrics is None:
        st.spinner("Syncing metrics...")
        st.stop()
        
    if not all_metrics:
        st.title("QuantifI")
        st.info("No active metrics. Restore archived metrics in Settings or create a new one.")
        return

    # --- 3. STATE INITIALIZATION ---
    if "tracker_view_selector" not in st.session_state:
        st.session_state["tracker_view_selector"] = "Overview"
    if "last_active_mid" not in st.session_state:
        st.session_state["last_active_mid"] = None

    # Apply Sticky and Pill CSS from utils
    utils.apply_custom_tabs_css()

    # Handle deep links via query parameters
    requested_mid = st.query_params.get("metric_id")
    if requested_mid:
        st.session_state["tracker_view_selector"] = "Record"
        st.session_state["last_active_mid"] = requested_mid
        st.query_params.clear()

    # --- 4. STICKY NAVIGATION HEADER ---
    view_options = ["Overview", "Record", "Analytics", "Edit"]
    
    with st.container():
        # Main Tab Selector
        st.segmented_control(
            "Navigation", 
            options=view_options, 
            selection_mode="single",
            label_visibility="collapsed",
            key="tracker_view_selector" 
        )
        
        view_mode = st.session_state["tracker_view_selector"]

        # Back Button Pill (visible on all sub-views)
        if view_mode != "Overview":
            utils.render_back_button(
                target_page_title="Tracker", 
                target_tab="Overview", 
                breadcrumb=view_mode
            )
#        st.divider()    

    # --- 5. METRIC SELECTION (Only for sub-views) ---
    selected_metric = None
    if view_mode != "Overview":
        active_id = st.session_state.get("last_active_mid")
        selected_metric = metrics.select_metric(all_metrics, target_id=active_id)
        
        if selected_metric:
            st.session_state["last_active_mid"] = selected_metric['id']

    # --- 6. CONTENT ROUTING ---
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
    
    # --- 1. PRE-RENDER NAVIGATION LOGIC (CRITICAL FIX) ---
    # The back button in settings points to Tracker/Overview.
    # We must catch the pill click and update state BEFORE the segmented control is built.
    back_pill_key = "pnav_Tracker_Overview"
    if st.session_state.get(back_pill_key) is not None:
        # Reset the pill selection
        st.session_state[back_pill_key] = None
        # Safely update the shared state for the Tracker page
        st.session_state["tracker_view_selector"] = "Overview"
        # Since we are on the 'Configure' page, we must manually switch back to 'Tracker'
        nav_pages = st.session_state.get("nav_pages", [])
        target_page = next((p for p in nav_pages if p.title == "Tracker"), None)
        if target_page:
            st.switch_page(target_page)

    st.title("Settings & Maintenance")
    
    # 2. Initialize local session state for settings tabs
    if "config_tab_selection" not in st.session_state:
        st.session_state["config_tab_selection"] = "📊 Edit Metric"

    # Apply CSS for stickiness and pills
    utils.apply_custom_tabs_css()

    # --- 3. STICKY HEADER CONTAINER ---
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
        
        # The key generated here (pnav_Tracker_Overview) matches the check at the top
        utils.render_back_button(
            target_page_title="Tracker", 
            target_tab="Overview", 
            breadcrumb=bc_text
        )
#        st.divider()

    # --- 4. DATA LOADING & CONTENT ROUTING ---
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